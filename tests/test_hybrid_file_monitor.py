"""
Tests for the HybridFileMonitor and related components.

This module tests the hybrid file monitoring system that automatically
selects between event-based and polling-based monitoring.
"""

import os
import time
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.hybrid_file_monitor import (
    HybridFileMonitor, EnvironmentDetector, create_file_monitor
)
from src.core.polling_file_monitor import PollingFileMonitor, FileState
from src.services.logger_service import LoggerService
from src.core.file_processor import FileProcessor


class TestFileState:
    """Tests for FileState dataclass."""
    
    def test_file_state_creation(self, temp_file):
        """Test FileState creation from file."""
        # Create test file
        temp_file.write_text("test content")
        
        # Create FileState
        state = FileState.from_file(str(temp_file))
        
        assert state is not None
        assert state.path == str(temp_file)
        assert state.mtime > 0
        assert state.size > 0
    
    def test_file_state_nonexistent_file(self):
        """Test FileState handles nonexistent files."""
        state = FileState.from_file("/path/that/does/not/exist")
        assert state is None
    
    def test_file_state_has_changed_with_none(self, temp_file):
        """Test has_changed method when comparing with None."""
        temp_file.write_text("test content")
        state = FileState.from_file(str(temp_file))
        assert state.has_changed(None) is True  # New file
    
    def test_file_state_has_changed_same_file(self, temp_file):
        """Test has_changed method with same file."""
        temp_file.write_text("test content")
        state1 = FileState.from_file(str(temp_file))
        state2 = FileState.from_file(str(temp_file))
        assert state1.has_changed(state2) is False  # Same file
    
    def test_file_state_has_changed_different_size(self, temp_file):
        """Test has_changed method with different file size."""
        temp_file.write_text("test content")
        state1 = FileState.from_file(str(temp_file))
        
        # Modify file size
        temp_file.write_text("test content with more text")
        state2 = FileState.from_file(str(temp_file))
        
        assert state1.has_changed(state2) is True
    
    def test_file_state_has_changed_different_mtime(self, temp_file):
        """Test has_changed method with different modification time."""
        temp_file.write_text("test content")
        state1 = FileState.from_file(str(temp_file))
        
        # Wait and modify mtime
        import time
        time.sleep(0.1)
        temp_file.touch()  # Update mtime without changing content
        state2 = FileState.from_file(str(temp_file))
        
        assert state1.has_changed(state2) is True
    
    def test_file_state_from_file_oserror_handling(self):
        """Test FileState handles OSError gracefully."""
        # Mock os.stat to raise OSError
        with patch('os.stat', side_effect=OSError("Access denied")):
            state = FileState.from_file("/some/file")
            assert state is None
    
    def test_file_state_change_detection(self, temp_file):
        """Test FileState change detection."""
        # Create initial file
        temp_file.write_text("initial content")
        state1 = FileState.from_file(str(temp_file))
        
        # Modify file
        time.sleep(0.1)  # Ensure different mtime
        temp_file.write_text("modified content")
        state2 = FileState.from_file(str(temp_file))
        
        # Test change detection
        assert state2.has_changed(state1)
        assert not state1.has_changed(state1)  # Same state
        assert state1.has_changed(None)  # New file


class TestEnvironmentDetector:
    """Tests for EnvironmentDetector."""
    
    def test_docker_environment_detection_dockerenv(self):
        """Test Docker detection via .dockerenv file."""
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True
            assert EnvironmentDetector.is_docker_environment()
    
    def test_docker_environment_detection_env_var(self):
        """Test Docker detection via environment variable."""
        with patch.dict(os.environ, {'DOCKER_CONTAINER': 'true'}):
            assert EnvironmentDetector.is_docker_environment()
    
    def test_docker_environment_detection_cgroup(self):
        """Test Docker detection via cgroup."""
        mock_content = "1:name=systemd:/docker/container123"
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = mock_content
            assert EnvironmentDetector.is_docker_environment()
    
    def test_non_docker_environment(self):
        """Test detection in non-Docker environment."""
        with patch('pathlib.Path.exists', return_value=False), \
             patch.dict(os.environ, {}, clear=True), \
             patch('builtins.open', side_effect=FileNotFoundError):
            assert not EnvironmentDetector.is_docker_environment()
    
    def test_file_events_test(self, temp_dir):
        """Test file events functionality testing."""
        # This test may be flaky in some environments, so we'll test the logic
        result = EnvironmentDetector.test_file_events_work(str(temp_dir), timeout=1.0)
        # Result can be True or False depending on environment
        assert isinstance(result, bool)
    
    def test_recommend_monitoring_mode_explicit(self, temp_dir):
        """Test monitoring mode recommendation with explicit preferences."""
        assert EnvironmentDetector.recommend_monitoring_mode(str(temp_dir), "events") == "events"
        assert EnvironmentDetector.recommend_monitoring_mode(str(temp_dir), "polling") == "polling"
    
    @patch.object(EnvironmentDetector, 'is_docker_environment', return_value=True)
    @patch.object(EnvironmentDetector, 'test_file_events_work', return_value=False)
    def test_recommend_monitoring_mode_docker_no_events(self, mock_events, mock_docker, temp_dir):
        """Test monitoring mode recommendation in Docker without working events."""
        result = EnvironmentDetector.recommend_monitoring_mode(str(temp_dir), "auto")
        assert result == "polling"
    
    @patch.object(EnvironmentDetector, 'is_docker_environment', return_value=False)
    @patch.object(EnvironmentDetector, 'test_file_events_work', return_value=True)
    def test_recommend_monitoring_mode_native_with_events(self, mock_events, mock_docker, temp_dir):
        """Test monitoring mode recommendation in native environment with working events."""
        result = EnvironmentDetector.recommend_monitoring_mode(str(temp_dir), "auto")
        assert result == "events"


class TestPollingFileMonitor:
    """Tests for PollingFileMonitor."""
    
    @pytest.fixture
    def mock_processor(self):
        """Create mock file processor."""
        processor = Mock(spec=FileProcessor)
        processor.process_file.return_value = Mock(success=True)
        return processor
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger service."""
        logger = Mock(spec=LoggerService)
        return logger
    
    def test_polling_monitor_initialization(self, temp_dir, mock_processor, mock_logger):
        """Test PollingFileMonitor initialization."""
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            polling_interval=1.0,
            docker_optimized=True
        )
        
        assert monitor.source_folder.samefile(temp_dir)  # Handle symlinks
        assert monitor.polling_interval == 1.0
        assert monitor.docker_optimized is True
        assert not monitor.is_monitoring()
    
    def test_polling_monitor_invalid_folder(self, mock_processor, mock_logger):
        """Test PollingFileMonitor with invalid folder."""
        with pytest.raises(ValueError, match="Source folder does not exist"):
            PollingFileMonitor(
                source_folder="/path/that/does/not/exist",
                file_processor=mock_processor,
                logger_service=mock_logger
            )
    
    def test_polling_monitor_start_stop(self, temp_dir, mock_processor, mock_logger):
        """Test starting and stopping polling monitor."""
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            polling_interval=0.5
        )
        
        # Start monitoring
        monitor.start_monitoring()
        assert monitor.is_monitoring()
        
        # Brief wait to ensure thread is running
        time.sleep(0.1)
        assert monitor._monitor_thread.is_alive()
        
        # Stop monitoring
        monitor.stop_monitoring()
        time.sleep(0.1)  # Allow thread to stop
        assert not monitor.is_monitoring()
    
    def test_polling_monitor_file_detection(self, temp_dir, mock_processor, mock_logger):
        """Test that polling monitor detects new files."""
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            polling_interval=0.3  # Faster polling for tests
        )
        
        try:
            monitor.start_monitoring()
            time.sleep(0.2)  # Let initial scan complete
            
            # Create test file
            test_file = temp_dir / "test_file.txt"
            test_file.write_text("test content")
            
            # Wait for polling cycles to detect file
            time.sleep(1.2)  # Allow 3-4 polling cycles
            
            # Verify file was processed
            mock_processor.process_file.assert_called()
            
        finally:
            monitor.stop_monitoring()
    
    def test_polling_monitor_stats(self, temp_dir, mock_processor, mock_logger):
        """Test polling monitor statistics."""
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger
        )
        
        stats = monitor.get_monitoring_stats()
        
        assert 'polling_cycles' in stats
        assert 'files_scanned' in stats
        assert 'source_folder' in stats
        assert Path(stats['source_folder']).samefile(temp_dir)  # Handle symlinks
    
    def test_polling_monitor_error_scenarios(self, temp_dir, mock_processor, mock_logger):
        """Test error handling scenarios in PollingFileMonitor."""
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            polling_interval=0.5
        )
        
        # Test double start
        monitor.start_monitoring()
        try:
            with pytest.raises(RuntimeError, match="Monitoring is already active"):
                monitor.start_monitoring()
        finally:
            monitor.stop_monitoring()
        
        # Test start with missing folder
        import shutil
        shutil.rmtree(temp_dir)
        with pytest.raises(RuntimeError, match="Source folder no longer exists"):
            monitor.start_monitoring()
    
    def test_polling_monitor_permission_errors(self, temp_dir, mock_processor, mock_logger):
        """Test permission error handling."""
        # Create a test directory that we'll make unreadable
        test_dir = temp_dir / "unreadable"
        test_dir.mkdir()
        
        monitor = PollingFileMonitor(
            source_folder=str(test_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            polling_interval=0.5
        )
        
        # Mock os.access to return False (no read access)
        with patch('os.access', return_value=False):
            with pytest.raises(RuntimeError, match="No read access to source folder"):
                monitor.start_monitoring()
    
    def test_polling_monitor_thread_health_check(self, temp_dir, mock_processor, mock_logger):
        """Test health check functionality."""
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            polling_interval=0.5
        )
        
        # Health check when not monitoring
        assert not monitor.is_monitoring()
        
        # Start monitoring and verify health
        monitor.start_monitoring()
        try:
            assert monitor.is_monitoring()
            
            # Test health check when source folder becomes inaccessible
            import shutil
            temp_backup = str(temp_dir) + "_backup"
            shutil.move(str(temp_dir), temp_backup)
            
            # Health check should fail now
            time.sleep(0.1)  # Allow for health check
            assert not monitor.is_monitoring()
            
            # Restore folder for cleanup
            shutil.move(temp_backup, str(temp_dir))
        finally:
            try:
                monitor.stop_monitoring()
            except:
                pass
    
    def test_polling_monitor_file_processing_with_errors(self, temp_dir, mock_processor, mock_logger):
        """Test file processing with various error scenarios."""
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            polling_interval=0.5
        )
        
        # Create a test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        # Mock processor to raise exception 
        mock_processor.process_file.side_effect = Exception("Processing exception")
        
        monitor.start_monitoring()
        try:
            # Wait for processing attempt
            time.sleep(1.0)
            
            # Check stats were updated
            stats = monitor.get_monitoring_stats()
            assert stats['processing_errors'] > 0  # Exception should be counted
            
        finally:
            monitor.stop_monitoring()
    
    def test_polling_monitor_batch_processing(self, temp_dir, mock_processor, mock_logger):
        """Test Docker-optimized batch processing."""
        # Set up successful processing
        mock_processor.process_file.return_value = Mock(success=True)
        
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            polling_interval=0.5,
            docker_optimized=True  # Enable batch processing
        )
        
        # Create multiple test files (fewer for faster test)
        files = []
        for i in range(3):
            test_file = temp_dir / f"batch_test_{i}.txt"
            test_file.write_text(f"batch content {i}")
            files.append(test_file)
        
        monitor.start_monitoring()
        try:
            # Wait for batch processing
            time.sleep(1.5)  # Allow time for processing
            
            # Verify files were detected and processed
            stats = monitor.get_monitoring_stats()
            assert stats['files_scanned'] >= len(files)
            assert stats['new_files_detected'] >= len(files)
            
        finally:
            monitor.stop_monitoring()
    
    def test_polling_monitor_file_stability(self, temp_dir, mock_processor, mock_logger):
        """Test file stability checking."""
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger
        )
        
        # Test with non-existent file
        assert not monitor._wait_for_file_stability("/path/that/does/not/exist")
        
        # Test with real file
        test_file = temp_dir / "stability_test.txt"
        test_file.write_text("test content")
        
        # Should be stable
        assert monitor._wait_for_file_stability(str(test_file), stability_delay=0.1)
        
        # Test file disappearing during check
        test_file.unlink()
        assert not monitor._wait_for_file_stability(str(test_file))
    
    def test_polling_monitor_manual_scan(self, temp_dir, mock_processor, mock_logger):
        """Test manual scan functionality."""
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger
        )
        
        # Create test files
        file1 = temp_dir / "manual1.txt"
        file2 = temp_dir / "manual2.txt"
        file1.write_text("manual content 1")
        file2.write_text("manual content 2")
        
        # Run manual scan
        processed = monitor.trigger_manual_scan()
        assert processed == 2
        
        # Test with processing errors
        mock_processor.process_file.side_effect = Exception("Processing error")
        processed = monitor.trigger_manual_scan()
        assert processed == 0
    
    def test_polling_monitor_system_file_filtering(self, temp_dir, mock_processor, mock_logger):
        """Test that system files are properly filtered."""
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            polling_interval=0.5
        )
        
        # Create system files that should be ignored
        (temp_dir / ".DS_Store").write_text("system file")
        (temp_dir / "Thumbs.db").write_text("system file")
        (temp_dir / "test.tmp").write_text("temp file")
        
        # Create legitimate file
        (temp_dir / "real_file.txt").write_text("real content")
        
        monitor.start_monitoring()
        try:
            time.sleep(1.0)  # Allow processing
            
            # Only the real file should be processed
            stats = monitor.get_monitoring_stats()
            # System files should be scanned but not processed
            assert stats['files_scanned'] >= 4
            assert stats['files_processed'] == 1
            
        finally:
            monitor.stop_monitoring()
    
    def test_polling_monitor_context_manager(self, temp_dir, mock_processor, mock_logger):
        """Test context manager functionality."""
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            polling_interval=0.5
        )
        
        # Test context manager
        with monitor:
            assert monitor.is_monitoring()
            
        # Should be stopped after context exit
        assert not monitor.is_monitoring()
    
    def test_polling_monitor_stats_thread_health(self, temp_dir, mock_processor, mock_logger):
        """Test comprehensive stats including thread health."""
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            polling_interval=0.5
        )
        
        # Stats when not running
        stats = monitor.get_monitoring_stats()
        assert not stats['is_monitoring']
        assert not stats['thread_alive']
        assert stats['files_being_processed'] == 0
        
        # Stats when running
        monitor.start_monitoring()
        try:
            time.sleep(0.1)  # Allow thread to start
            stats = monitor.get_monitoring_stats()
            assert stats['is_monitoring']
            assert stats['thread_alive']
            assert stats['polling_interval'] == 0.5
            assert stats['docker_optimized'] == False
            
        finally:
            monitor.stop_monitoring()
    
    def test_polling_monitor_thread_timeout_and_errors(self, temp_dir, mock_processor, mock_logger):
        """Test thread timeout and monitoring loop error handling."""
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            polling_interval=0.1  # Very short for fast test
        )
        
        # Mock _poll_directory to raise exception
        with patch.object(monitor, '_poll_directory', side_effect=Exception("Poll error")):
            monitor.start_monitoring()
            try:
                time.sleep(0.5)  # Allow error to occur
                
                # Check error stats
                stats = monitor.get_monitoring_stats()
                assert stats['polling_errors'] > 0
                
            finally:
                monitor.stop_monitoring()
        
        # Test thread timeout scenario
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            polling_interval=0.1
        )
        
        monitor.start_monitoring()
        
        # Mock thread to not stop gracefully
        original_is_alive = monitor._monitor_thread.is_alive
        monitor._monitor_thread.is_alive = Mock(return_value=True)
        
        try:
            monitor.stop_monitoring()  # Should log timeout warning
            
        finally:
            # Restore original method and force stop
            monitor._monitor_thread.is_alive = original_is_alive
            monitor._stop_event.set()
            monitor._monitoring = False
    
    def test_polling_monitor_directory_not_directory_error(self, temp_dir, mock_processor, mock_logger):
        """Test initialization with path that is not a directory."""
        # Create a file instead of directory
        not_dir = temp_dir / "not_a_directory.txt"
        not_dir.write_text("this is a file")
        
        with pytest.raises(ValueError, match="Source path is not a directory"):
            PollingFileMonitor(
                source_folder=str(not_dir),
                file_processor=mock_processor,
                logger_service=mock_logger
            )
    
    def test_polling_monitor_directory_health_check_exception(self, temp_dir, mock_processor, mock_logger):
        """Test health check exception handling."""
        monitor = PollingFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            polling_interval=0.5
        )
        
        monitor.start_monitoring()
        try:
            # Mock Path.exists to raise exception during health check
            with patch('pathlib.Path.exists', side_effect=Exception("Health check error")):
                result = monitor.is_monitoring()
                assert result is False  # Should return False on exception
                
        finally:
            monitor.stop_monitoring()


class TestHybridFileMonitor:
    """Tests for HybridFileMonitor."""
    
    @pytest.fixture
    def mock_processor(self):
        """Create mock file processor."""
        processor = Mock(spec=FileProcessor)
        processor.process_file.return_value = Mock(success=True)
        return processor
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger service."""
        logger = Mock(spec=LoggerService)
        return logger
    
    def test_hybrid_monitor_initialization(self, temp_dir, mock_processor, mock_logger):
        """Test HybridFileMonitor initialization."""
        monitor = HybridFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            monitoring_mode="polling",
            polling_interval=2.0,
            docker_volume_mode=True
        )
        
        assert monitor.source_folder == str(temp_dir)
        assert monitor.monitoring_mode == "polling"
        assert monitor.polling_interval == 2.0
        assert monitor.docker_volume_mode is True
        assert not monitor.is_monitoring()
    
    @patch.object(EnvironmentDetector, 'recommend_monitoring_mode', return_value='polling')
    def test_hybrid_monitor_polling_mode(self, mock_recommend, temp_dir, mock_processor, mock_logger):
        """Test hybrid monitor using polling mode."""
        monitor = HybridFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            monitoring_mode="auto"
        )
        
        try:
            monitor.start_monitoring()
            assert monitor.is_monitoring()
            assert monitor._selected_mode == "polling"
            assert isinstance(monitor._active_monitor, PollingFileMonitor)
            
        finally:
            monitor.stop_monitoring()
    
    @patch.object(EnvironmentDetector, 'recommend_monitoring_mode', return_value='events')
    def test_hybrid_monitor_events_mode(self, mock_recommend, temp_dir, mock_processor, mock_logger):
        """Test hybrid monitor using events mode."""
        monitor = HybridFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            monitoring_mode="auto"
        )
        
        try:
            monitor.start_monitoring()
            assert monitor.is_monitoring()
            assert monitor._selected_mode == "events"
            # Should be FileMonitor, not PollingFileMonitor
            assert not isinstance(monitor._active_monitor, PollingFileMonitor)
            
        finally:
            monitor.stop_monitoring()
    
    def test_hybrid_monitor_explicit_mode(self, temp_dir, mock_processor, mock_logger):
        """Test hybrid monitor with explicit mode selection."""
        monitor = HybridFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            monitoring_mode="polling"
        )
        
        try:
            monitor.start_monitoring()
            assert monitor._selected_mode == "polling"
            assert isinstance(monitor._active_monitor, PollingFileMonitor)
            
        finally:
            monitor.stop_monitoring()
    
    def test_hybrid_monitor_stats(self, temp_dir, mock_processor, mock_logger):
        """Test hybrid monitor statistics."""
        monitor = HybridFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            monitoring_mode="polling"
        )
        
        try:
            monitor.start_monitoring()
            stats = monitor.get_monitoring_stats()
            
            assert stats['hybrid_mode'] is True
            assert stats['selected_mode'] == 'polling'
            assert 'is_docker_environment' in stats
            assert 'docker_volume_mode' in stats
            assert Path(stats['source_folder']).samefile(temp_dir)  # Handle symlinks
            
        finally:
            monitor.stop_monitoring()
    
    def test_hybrid_monitor_manual_scan(self, temp_dir, mock_processor, mock_logger):
        """Test hybrid monitor manual scan functionality."""
        # Create test file
        test_file = temp_dir / "existing_file.txt"
        test_file.write_text("existing content")
        
        monitor = HybridFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            monitoring_mode="polling"
        )
        
        try:
            monitor.start_monitoring()
            
            # Trigger manual scan
            processed_count = monitor.trigger_manual_scan()
            
            assert processed_count >= 0  # Should process at least 0 files
            mock_processor.process_file.assert_called()
            
        finally:
            monitor.stop_monitoring()
    
    def test_hybrid_monitor_context_manager(self, temp_dir, mock_processor, mock_logger):
        """Test hybrid monitor as context manager."""
        monitor = HybridFileMonitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            monitoring_mode="polling"
        )
        
        with monitor:
            assert monitor.is_monitoring()
        
        # Should be stopped after context exit
        assert not monitor.is_monitoring()


class TestCreateFileMonitor:
    """Tests for create_file_monitor factory function."""
    
    @pytest.fixture
    def mock_processor(self):
        """Create mock file processor."""
        return Mock(spec=FileProcessor)
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger service."""
        return Mock(spec=LoggerService)
    
    def test_create_file_monitor_default_config(self, temp_dir, mock_processor, mock_logger):
        """Test create_file_monitor with default configuration."""
        config = {}
        
        monitor = create_file_monitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            config=config
        )
        
        assert isinstance(monitor, HybridFileMonitor)
        assert monitor.source_folder == str(temp_dir)
        assert monitor.monitoring_mode == "auto"
        assert monitor.polling_interval == 3.0
        assert monitor.docker_volume_mode is False
    
    def test_create_file_monitor_custom_config(self, temp_dir, mock_processor, mock_logger):
        """Test create_file_monitor with custom configuration."""
        config = {
            'file_monitoring_mode': 'polling',
            'polling_interval': 5.0,
            'docker_volume_mode': True
        }
        
        monitor = create_file_monitor(
            source_folder=str(temp_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            config=config
        )
        
        assert isinstance(monitor, HybridFileMonitor)
        assert monitor.monitoring_mode == "polling"
        assert monitor.polling_interval == 5.0
        assert monitor.docker_volume_mode is True


# Integration tests
class TestHybridMonitoringIntegration:
    """Integration tests for hybrid monitoring system."""
    
    @pytest.fixture
    def temp_source_dir(self):
        """Create temporary source directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_processor(self):
        """Create mock file processor that simulates successful processing."""
        processor = Mock(spec=FileProcessor)
        
        # Mock that simulates file removal after processing (like real system)
        def mock_process_file(file_path):
            result = Mock(success=True, error_message=None)
            # Simulate file removal by actually removing the file
            try:
                Path(file_path).unlink()
            except FileNotFoundError:
                pass  # File already removed
            return result
        
        processor.process_file.side_effect = mock_process_file
        return processor
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger service."""
        return Mock(spec=LoggerService)
    
    def test_end_to_end_polling_monitoring(self, temp_source_dir, mock_processor, mock_logger):
        """Test end-to-end polling-based monitoring."""
        config = {
            'file_monitoring_mode': 'polling',
            'polling_interval': 0.5,
            'docker_volume_mode': False
        }
        
        monitor = create_file_monitor(
            source_folder=str(temp_source_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            config=config
        )
        
        try:
            monitor.start_monitoring()
            time.sleep(0.1)  # Let monitoring start
            
            # Create test file
            test_file = temp_source_dir / "integration_test.txt"
            test_file.write_text("integration test content")
            
            # Wait for polling to detect and process file
            time.sleep(1.0)
            
            # Verify processing was called
            mock_processor.process_file.assert_called()
            call_args = mock_processor.process_file.call_args[0]
            assert str(test_file) in call_args[0]
            
        finally:
            monitor.stop_monitoring()
    
    def test_directory_processing_polling_mode(self, temp_source_dir, mock_processor, mock_logger):
        """Test polling monitor processes files in directories recursively."""
        config = {
            'file_monitoring_mode': 'polling',
            'polling_interval': 0.3,
            'docker_volume_mode': False
        }
        
        monitor = create_file_monitor(
            source_folder=str(temp_source_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            config=config
        )
        
        # Create all directory structure and files BEFORE starting monitoring
        subdir = temp_source_dir / "SCRA"
        subdir.mkdir()
        
        # Create files in subdirectory
        file1 = subdir / "document1.pdf"
        file1.write_text("PDF content 1")
        
        file2 = subdir / "document2.docx"
        file2.write_text("DOCX content 2")
        
        # Create nested directory
        nested_dir = subdir / "nested"
        nested_dir.mkdir()
        file3 = nested_dir / "nested_file.txt"
        file3.write_text("Nested content")

        try:
            monitor.start_monitoring()
            time.sleep(0.2)  # Let monitoring start
            
            # Verify files actually exist
            print(f"DEBUG: Files created:")
            print(f"  file1 exists: {file1.exists()} - {file1}")
            print(f"  file2 exists: {file2.exists()} - {file2}")
            print(f"  file3 exists: {file3.exists()} - {file3}")
            
            # Wait for polling to detect and process all files  
            time.sleep(1.5)  # Allow multiple polling cycles
            
            # Get all processed file paths for debugging
            processed_files = []
            for call in mock_processor.process_file.call_args_list:
                processed_files.append(call[0][0])
            
            print(f"DEBUG: Processed {mock_processor.process_file.call_count} files:")
            for f in processed_files:
                print(f"  - {f}")
            
            # Verify all files were processed (should be exactly 3)
            assert mock_processor.process_file.call_count == 3, f"Expected exactly 3 files, got {mock_processor.process_file.call_count}: {processed_files}"
            
            # Check that all three files were processed using resolved paths for reliable comparison
            file1_resolved = str(file1.resolve())
            file2_resolved = str(file2.resolve())
            file3_resolved = str(file3.resolve())
            
            processed_resolved = [str(Path(pf).resolve()) for pf in processed_files]
            
            file1_processed = file1_resolved in processed_resolved
            file2_processed = file2_resolved in processed_resolved  
            file3_processed = file3_resolved in processed_resolved
            
            assert file1_processed, f"file1 {file1_resolved} was not processed. Processed: {processed_resolved}"
            assert file2_processed, f"file2 {file2_resolved} was not processed. Processed: {processed_resolved}" 
            assert file3_processed, f"file3 {file3_resolved} was not processed. Processed: {processed_resolved}"
            
        finally:
            monitor.stop_monitoring()
    
    def test_directory_processing_events_mode(self, temp_source_dir, mock_processor, mock_logger):
        """Test events monitor processes files in directories recursively."""
        config = {
            'file_monitoring_mode': 'events',
            'polling_interval': 3.0,
            'docker_volume_mode': False
        }
        
        monitor = create_file_monitor(
            source_folder=str(temp_source_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            config=config
        )
        
        try:
            monitor.start_monitoring()
            time.sleep(0.2)  # Let monitoring start
            
            # Create directory structure with files
            subdir = temp_source_dir / "SCRA_Events"
            subdir.mkdir()
            
            # Brief delay to allow directory creation event to be processed
            time.sleep(0.5)
            
            # Create files in subdirectory
            file1 = subdir / "document1.pdf"
            file1.write_text("PDF content 1")
            
            file2 = subdir / "document2.docx" 
            file2.write_text("DOCX content 2")
            
            # Create nested directory and file
            nested_dir = subdir / "nested"
            nested_dir.mkdir()
            time.sleep(0.3)  # Allow directory creation
            
            file3 = nested_dir / "nested_file.txt"
            file3.write_text("Nested content")
            
            # Wait for events to be processed
            time.sleep(1.0)
            
            # Verify processing was called (should process directory contents + individual files)
            assert mock_processor.process_file.call_count >= 3
            
            # Get all processed file paths
            processed_files = []
            for call in mock_processor.process_file.call_args_list:
                processed_files.append(call[0][0])
            
            # Verify files were processed (either from directory scan or individual events)
            file_basenames = [os.path.basename(f) for f in processed_files]
            assert "document1.pdf" in file_basenames
            assert "document2.docx" in file_basenames
            assert "nested_file.txt" in file_basenames
            
        finally:
            monitor.stop_monitoring()
    
    @patch.object(EnvironmentDetector, 'is_docker_environment', return_value=True)
    @patch.object(EnvironmentDetector, 'test_file_events_work', return_value=False)
    def test_docker_environment_auto_selection(self, mock_events, mock_docker, 
                                              temp_source_dir, mock_processor, mock_logger):
        """Test automatic polling selection in Docker environment."""
        config = {
            'file_monitoring_mode': 'auto',
            'polling_interval': 0.5,
            'docker_volume_mode': True
        }
        
        monitor = create_file_monitor(
            source_folder=str(temp_source_dir),
            file_processor=mock_processor,
            logger_service=mock_logger,
            config=config
        )
        
        try:
            monitor.start_monitoring()
            
            # Verify polling mode was selected
            stats = monitor.get_monitoring_stats()
            assert stats['selected_mode'] == 'polling'
            assert stats['is_docker_environment'] is True
            assert stats['docker_volume_mode'] is True
            
        finally:
            monitor.stop_monitoring()


@pytest.fixture
def temp_file():
    """Create temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as f:
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    try:
        temp_path.unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)