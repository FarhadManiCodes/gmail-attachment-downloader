"""
Attachment downloader with smart organization and async support
"""

import asyncio
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

class AttachmentDownloader:
    """Handle attachment downloads with organization"""
    
    def __init__(self, base_dir: str, organize_by: str = "sender"):
        """Initialize downloader with base directory and organization strategy"""
        self.base_dir = Path(base_dir)
        self.organize_by = organize_by  # sender, date, flat
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    async def download_attachment(self, 
                                attachment_data: bytes,
                                filename: str,
                                sender: str,
                                date: datetime) -> Path:
        """Download and save attachment to organized folder"""
        
        # Get organized path
        download_path = self.get_download_path(filename, sender, date)
        download_path.parent.mkdir(parents=True, exist_ok=True)
        
        # TODO: Implement async file writing
        print(f"💾 Downloading to: {download_path}")
        
        # async with aiofiles.open(download_path, 'wb') as f:
        #     await f.write(attachment_data)
        
        return download_path
    
    def get_download_path(self, filename: str, sender: str, date: datetime) -> Path:
        """Generate organized download path based on strategy"""
        
        # Sanitize filename
        safe_filename = self.sanitize_filename(filename)
        
        if self.organize_by == "sender":
            safe_sender = self.sanitize_filename(sender.split("@")[0])
            return self.base_dir / safe_sender / safe_filename
        
        elif self.organize_by == "date":
            date_folder = date.strftime("%Y-%m-%d")
            return self.base_dir / date_folder / safe_filename
        
        elif self.organize_by == "flat":
            return self.base_dir / safe_filename
        
        else:
            # Default to sender organization
            safe_sender = self.sanitize_filename(sender.split("@")[0])
            return self.base_dir / safe_sender / safe_filename
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file system operations"""
        # TODO: Implement proper filename sanitization
        # Remove or replace unsafe characters
        unsafe_chars = '<>:"/\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
    
    def is_valid_attachment(self, 
                          filename: str, 
                          size: int,
                          allowed_extensions: List[str],
                          min_size: int = 1024,
                          max_size: int = 50 * 1024 * 1024) -> bool:
        """Check if attachment meets filter criteria"""
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if allowed_extensions and file_ext not in allowed_extensions:
            return False
        
        # Check file size
        if size < min_size or size > max_size:
            return False
        
        return True


class EmailWatcher:
    """Watch for new emails in real-time"""
    
    def __init__(self, gmail_client, downloader: AttachmentDownloader):
        """Initialize email watcher"""
        self.gmail_client = gmail_client
        self.downloader = downloader
        self.is_watching = False
    
    async def start_watching(self, 
                           filters: Dict[str, Any],
                           check_interval: int = 30):
        """Start watching for new emails"""
        
        print(f"👀 Starting email watch mode (checking every {check_interval}s)")
        self.is_watching = True
        
        # TODO: Implement real-time email monitoring
        while self.is_watching:
            print("🔄 Checking for new emails...")
            # Check for new emails with filters
            # Download any new attachments
            await asyncio.sleep(check_interval)
    
    def stop_watching(self):
        """Stop watching for emails"""
        print("⏹️ Stopping email watch")
        self.is_watching = False
