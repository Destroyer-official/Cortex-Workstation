import os
import random
import logging
import stat

class WeaponizedShredder:
    """Implements Military-Grade File Shredding Algorithms (DoD 5220.22-M)."""
    
    def __init__(self):
        self.logger = logging.getLogger('weaponized_shredder')
        
    def shred_file(self, file_path: str, passes: int = 3) -> bool:
        """
        Shreds a file using the DoD 5220.22-M standard loosely (or custom passes).
        Pass 1: Zeros
        Pass 2: Ones
        Pass 3+: Random Data
        """
        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            return False
            
        try:
            # Ensure we can write to the file
            os.chmod(file_path, stat.S_IWRITE)
            file_size = os.path.getsize(file_path)
            
            with open(file_path, 'r+b') as f:
                for p in range(1, passes + 1):
                    f.seek(0)
                    if p == 1:
                        # Zeros
                        f.write(b'\x00' * file_size)
                    elif p == 2:
                        # Ones
                        f.write(b'\xFF' * file_size)
                    else:
                        # Random
                        # Writing in chunks for large files
                        chunk_size = 1024 * 1024 # 1MB
                        bytes_written = 0
                        while bytes_written < file_size:
                            write_size = min(chunk_size, file_size - bytes_written)
                            f.write(os.urandom(write_size))
                            bytes_written += write_size
                            
                    # Flush to disk natively
                    f.flush()
                    os.fsync(f.fileno())
                    
            # Obfuscate filename before deletion to clear MFT entry
            dir_name = os.path.dirname(file_path)
            base_ext = os.path.splitext(file_path)[1]
            rand_name = os.path.join(dir_name, str(random.randint(100000, 999999)) + base_ext)
            os.rename(file_path, rand_name)
            
            # Final deletion
            os.remove(rand_name)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to shred file {file_path}: {e}")
            return False
            
    def shred_directory(self, dir_path: str, passes: int = 3) -> bool:
        """Recursively shreds a directory and its contents."""
        success = True
        for root, dirs, files in os.walk(dir_path, topdown=False):
            for file in files:
                filepath = os.path.join(root, file)
                if not self.shred_file(filepath, passes):
                    success = False
                    
            for d in dirs:
                dirpath = os.path.join(root, d)
                try:
                    os.rmdir(dirpath)
                except:
                    success = False
                    
        try:
            os.rmdir(dir_path)
        except:
            success = False
            
        return success
