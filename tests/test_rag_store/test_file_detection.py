"""
Tests for File Content Detection

This module tests the file content detection utilities for distinguishing
between actual DOC files and RTF files with .doc extensions.
"""

import tempfile
import unittest
from pathlib import Path


class TestFileContentDetector(unittest.TestCase):
    """Test cases for file content detection functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def create_rtf_content_file(self, filename: str, content: str = None) -> Path:
        """Create a test file with RTF content."""
        if content is None:
            content = r"""{\rtf1\ansi\deff0 
{\fonttbl {\f0 Times New Roman;}}
\f0\fs24 This is a test RTF document.
\par
Second paragraph with more content.
}"""
        
        file_path = self.temp_path / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    def create_doc_content_file(self, filename: str) -> Path:
        """Create a test file with mock DOC content (OLE2 signature)."""
        # OLE2 signature for MS Word documents
        ole2_signature = b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'
        mock_doc_content = ole2_signature + b'\x00' * 100 + b'Microsoft Office Word' + b'\x00' * 1000
        
        file_path = self.temp_path / filename
        with open(file_path, 'wb') as f:
            f.write(mock_doc_content)
        return file_path
    
    def create_text_file(self, filename: str, content: str = "Plain text content") -> Path:
        """Create a plain text file."""
        file_path = self.temp_path / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path

    def test_detect_rtf_content_positive(self):
        """Test RTF content detection with valid RTF files."""
        from src.rag_store.file_detection import FileContentDetector
        
        # Test standard RTF file
        rtf_file = self.create_rtf_content_file("test.rtf")
        self.assertTrue(FileContentDetector._is_rtf_content(
            open(rtf_file, 'rb').read(1024),
            open(rtf_file, 'r', encoding='utf-8', errors='ignore').read(1024)
        ))
        
        # Test RTF file with .doc extension
        rtf_as_doc = self.create_rtf_content_file("test.doc")
        result = FileContentDetector.detect_doc_file_type(rtf_as_doc)
        self.assertEqual(result, "rtf")
        
        # Test RTF content with minimal RTF structure
        minimal_rtf = self.create_rtf_content_file("minimal.rtf", r"{\rtf1\ansi Hello World}")
        result = FileContentDetector.detect_doc_file_type(minimal_rtf)
        self.assertEqual(result, "rtf")

    def test_detect_rtf_content_negative(self):
        """Test RTF content detection with non-RTF files."""
        from src.rag_store.file_detection import FileContentDetector
        
        # Test plain text file
        text_file = self.create_text_file("test.txt", "This is plain text, not RTF.")
        result = FileContentDetector.detect_doc_file_type(text_file)
        self.assertNotEqual(result, "rtf")
        
        # Test text that mentions RTF but isn't RTF
        fake_rtf = self.create_text_file("fake.txt", "This mentions \\rtf but is not RTF format")
        header = open(fake_rtf, 'r', encoding='utf-8', errors='ignore').read(1024)
        self.assertFalse(FileContentDetector._is_rtf_content(b"", header))

    def test_detect_doc_content_positive(self):
        """Test DOC content detection with valid DOC files."""
        from src.rag_store.file_detection import FileContentDetector
        
        # Test file with OLE2 signature
        doc_file = self.create_doc_content_file("test.doc")
        result = FileContentDetector.detect_doc_file_type(doc_file)
        self.assertEqual(result, "doc")

    def test_detect_doc_content_negative(self):
        """Test DOC content detection with non-DOC files."""
        from src.rag_store.file_detection import FileContentDetector
        
        # Test plain text file
        text_file = self.create_text_file("test.txt")
        header_bytes = open(text_file, 'rb').read(1024)
        header_str = open(text_file, 'r', encoding='utf-8', errors='ignore').read(1024)
        self.assertFalse(FileContentDetector._is_doc_content(header_bytes, header_str))

    def test_detect_doc_file_type_comprehensive(self):
        """Test comprehensive .doc file type detection."""
        from src.rag_store.file_detection import FileContentDetector
        
        # RTF content with .doc extension
        rtf_as_doc = self.create_rtf_content_file("rtf_file.doc")
        self.assertEqual(FileContentDetector.detect_doc_file_type(rtf_as_doc), "rtf")
        
        # Actual DOC content
        doc_file = self.create_doc_content_file("real_doc.doc")
        self.assertEqual(FileContentDetector.detect_doc_file_type(doc_file), "doc")
        
        # Plain text with .doc extension (should be unknown)
        text_as_doc = self.create_text_file("text_file.doc", "Just plain text")
        self.assertEqual(FileContentDetector.detect_doc_file_type(text_as_doc), "unknown")

    def test_should_use_rtf_processor(self):
        """Test RTF processor routing logic."""
        from src.rag_store.file_detection import FileContentDetector
        
        # .rtf files should always use RTF processor
        rtf_file = self.create_rtf_content_file("test.rtf")
        self.assertTrue(FileContentDetector.should_use_rtf_processor(rtf_file))
        
        # .doc file with RTF content should use RTF processor
        rtf_as_doc = self.create_rtf_content_file("test.doc")
        self.assertTrue(FileContentDetector.should_use_rtf_processor(rtf_as_doc))
        
        # .doc file with actual DOC content should not use RTF processor
        doc_file = self.create_doc_content_file("test.doc")
        self.assertFalse(FileContentDetector.should_use_rtf_processor(doc_file))
        
        # Other file types should not use RTF processor
        text_file = self.create_text_file("test.txt")
        self.assertFalse(FileContentDetector.should_use_rtf_processor(text_file))

    def test_should_use_word_processor(self):
        """Test Word processor routing logic."""
        from src.rag_store.file_detection import FileContentDetector
        
        # .docx files should always use Word processor
        docx_path = Path("test.docx")
        self.assertTrue(FileContentDetector.should_use_word_processor(docx_path))
        
        # .doc file with actual DOC content should use Word processor
        doc_file = self.create_doc_content_file("test.doc")
        self.assertTrue(FileContentDetector.should_use_word_processor(doc_file))
        
        # .doc file with RTF content should not use Word processor
        rtf_as_doc = self.create_rtf_content_file("test.doc")
        self.assertFalse(FileContentDetector.should_use_word_processor(rtf_as_doc))
        
        # .doc file with unknown content should use Word processor (default)
        unknown_as_doc = self.create_text_file("unknown.doc", "Unknown content")
        self.assertTrue(FileContentDetector.should_use_word_processor(unknown_as_doc))
        
        # Other file types should not use Word processor
        text_file = self.create_text_file("test.txt")
        self.assertFalse(FileContentDetector.should_use_word_processor(text_file))

    def test_error_handling(self):
        """Test error handling in file detection."""
        from src.rag_store.file_detection import FileContentDetector
        
        # Non-existent file should return unknown
        nonexistent = Path("does_not_exist.doc")
        result = FileContentDetector.detect_doc_file_type(nonexistent)
        self.assertEqual(result, "unknown")

    def test_edge_cases(self):
        """Test edge cases in file detection."""
        from src.rag_store.file_detection import FileContentDetector
        
        # Empty file
        empty_file = self.temp_path / "empty.doc"
        empty_file.touch()
        result = FileContentDetector.detect_doc_file_type(empty_file)
        self.assertEqual(result, "unknown")
        
        # Very small RTF file
        tiny_rtf = self.create_rtf_content_file("tiny.doc", r"{\rtf1 Hi}")
        result = FileContentDetector.detect_doc_file_type(tiny_rtf)
        self.assertEqual(result, "rtf")
        
        # File with RTF-like patterns but not complete RTF
        partial_rtf = self.create_text_file("partial.doc", r"Some text with {\rtf in the middle")
        result = FileContentDetector.detect_doc_file_type(partial_rtf)
        self.assertEqual(result, "unknown")

    def test_case_insensitive_extensions(self):
        """Test that file extension checking is case insensitive."""
        from src.rag_store.file_detection import FileContentDetector
        
        # Test various case combinations
        extensions = [".rtf", ".RTF", ".Rtf", ".rTf"]
        
        for ext in extensions:
            file_path = Path(f"test{ext}")
            self.assertTrue(FileContentDetector.should_use_rtf_processor(
                self.create_rtf_content_file(f"test{ext}")
            ))

    def test_rtf_pattern_detection(self):
        """Test various RTF pattern detection scenarios."""
        from src.rag_store.file_detection import FileContentDetector
        
        # Test different RTF versions and patterns
        rtf_variations = [
            r"{\rtf1\ansi\deff0 Basic RTF}",
            r"{\rtf1\ansi\ansicpg1252\deff0 RTF with code page}",
            r"{\rtf1\ansi\deff0{\fonttbl{\f0 Arial;}} RTF with font table}",
            r"{\rtf1\ansi\deff0{\colortbl;\red255\green0\blue0;} RTF with colors}",
        ]
        
        for i, rtf_content in enumerate(rtf_variations):
            rtf_file = self.create_rtf_content_file(f"variation_{i}.doc", rtf_content)
            result = FileContentDetector.detect_doc_file_type(rtf_file)
            self.assertEqual(result, "rtf", f"Failed to detect RTF in variation {i}")


if __name__ == '__main__':
    unittest.main()