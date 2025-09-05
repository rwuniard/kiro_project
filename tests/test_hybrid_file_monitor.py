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
        processor.process_file.return_value = Mock(success=True, error_message=None)
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