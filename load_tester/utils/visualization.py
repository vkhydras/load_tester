"""
Visualization Utilities Module

This module provides terminal-based visualization helpers.
"""

import os
import sys
import shutil
from typing import List, Dict, Any, Optional, Tuple


def get_terminal_size() -> Tuple[int, int]:
    """
    Get the terminal size.
    
    Returns:
        Tuple of (width, height)
    """
    try:
        columns, lines = shutil.get_terminal_size()
        return columns, lines
    except Exception:
        # Default to 80x24 if we can't get the terminal size
        return 80, 24


def create_progress_bar(progress: float, width: int = 30, fill_char: str = '#', empty_char: str = ' ') -> str:
    """
    Create a text-based progress bar.
    
    Args:
        progress: Progress value (0.0 to 1.0)
        width: Width of the progress bar
        fill_char: Character to use for the filled portion
        empty_char: Character to use for the empty portion
        
    Returns:
        Progress bar string
    """
    # Ensure progress is between 0 and 1
    progress = max(0.0, min(1.0, progress))
    
    # Calculate filled and empty parts
    filled = int(width * progress)
    empty = width - filled
    
    # Create the bar
    bar = f"[{fill_char * filled}{empty_char * empty}]"
    
    return bar


def display_status_line(
    elapsed: float, 
    active_users: int, 
    completed_requests: int, 
    rps: float, 
    response_time: float,
    progress: float,
    status: str = ""
) -> None:
    """
    Display a status line with test progress.
    
    Args:
        elapsed: Elapsed time in seconds
        active_users: Number of active users
        completed_requests: Number of completed requests
        rps: Requests per second
        response_time: Average response time in seconds
        progress: Progress value (0.0 to 1.0)
        status: Status message
    """
    # Get terminal width
    terminal_width, _ = get_terminal_size()
    
    # Create progress bar
    bar_width = min(30, max(10, terminal_width - 70))
    progress_bar = create_progress_bar(progress, width=bar_width)
    
    # Format status line
    status_format = "{elapsed:5.1f}s | {users:3d} users | {reqs:5d} reqs | {rps:6.1f} req/s | {rt:6.1f} ms | {bar}"
    status_line = status_format.format(
        elapsed=elapsed,
        users=active_users,
        reqs=completed_requests,
        rps=rps,
        rt=response_time * 1000,  # Convert to ms
        bar=progress_bar
    )
    
    # Add status message if provided
    if status:
        status_line += f" {status}"
    
    # Truncate to terminal width
    if len(status_line) > terminal_width:
        status_line = status_line[:terminal_width - 3] + "..."
    
    # Print with carriage return
    print(f"\r{status_line}", end="", flush=True)


def create_histogram(data: List[float], bins: int = 10, width: int = 40, title: Optional[str] = None) -> str:
    """
    Create a text-based histogram.
    
    Args:
        data: List of values to create a histogram for
        bins: Number of bins
        width: Width of the histogram bars
        title: Optional title for the histogram
        
    Returns:
        Histogram string
    """
    if not data:
        return "No data to display"
    
    # Calculate min and max values
    min_val = min(data)
    max_val = max(data)
    
    # Ensure min and max are different
    if min_val == max_val:
        min_val = min_val - 0.5
        max_val = max_val + 0.5
    
    # Calculate bin width
    bin_width = (max_val - min_val) / bins
    
    # Create bins
    histogram = [0] * bins
    for value in data:
        bin_index = min(bins - 1, int((value - min_val) / bin_width))
        histogram[bin_index] += 1
    
    # Find the maximum bin count for scaling
    max_count = max(histogram)
    
    # Create the output string
    output = []
    
    if title:
        output.append(title)
        output.append('-' * len(title))
    
    for i in range(bins):
        bin_start = min_val + i * bin_width
        bin_end = min_val + (i + 1) * bin_width
        count = histogram[i]
        
        # Calculate bar length
        bar_length = int(width * count / max_count) if max_count > 0 else 0
        
        # Format bin range
        bin_range = f"{bin_start:6.2f} - {bin_end:6.2f}"
        
        # Format count
        count_str = f"{count:5d}"
        
        # Create bar
        bar = '#' * bar_length
        
        # Create line
        line = f"{bin_range} | {count_str} | {bar}"
        output.append(line)
    
    return '\n'.join(output)


def clear_screen() -> None:
    """Clear the terminal screen"""
    if sys.platform == 'win32':
        os.system('cls')
    else:
        os.system('clear')


def print_banner(text: str, width: Optional[int] = None, char: str = "=") -> None:
    """
    Print a banner with the given text.
    
    Args:
        text: Text to display in the banner
        width: Width of the banner (default: terminal width)
        char: Character to use for the banner
    """
    if width is None:
        width, _ = get_terminal_size()
    
    banner = char * width
    padding = (width - len(text) - 2) // 2
    
    print(banner)
    print(f"{char}{' ' * padding}{text}{' ' * (width - padding - len(text) - 2)}{char}")
    print(banner)