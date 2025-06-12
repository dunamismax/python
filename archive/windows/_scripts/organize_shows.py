import os
import shutil
import re

# --- Configuration ---
# 1. Set this to the folder where your original files are located.
SOURCE_DIRECTORY = r"C:\Users\admin\Downloads"

# 2. Set this to True to see what the script *would* do without actually moving files.
#    Set it to False to perform the actual move and rename operations.
DRY_RUN = False
# --- End of Configuration ---


def organize_tv_show():
    """
    Scans the source directory for 'Just The Ten Of Us' files,
    creates a new organized folder structure, and moves/renames the files.
    """
    show_name = "Just The Ten Of Us"
    main_destination_folder = os.path.join(SOURCE_DIRECTORY, show_name)

    print(f"Starting organization for '{show_name}'...")
    print(f"Source Directory: {SOURCE_DIRECTORY}")
    if DRY_RUN:
        print("\n*** DRY RUN IS ENABLED. NO FILES WILL BE MOVED OR RENAMED. ***\n")
    else:
        print("\n*** LIVE RUN. FILES WILL BE MOVED AND RENAMED. ***\n")

    # --- Step 1: Create the main and season folders ---
    try:
        print(f"Creating main folder: {main_destination_folder}")
        if not DRY_RUN:
            os.makedirs(main_destination_folder, exist_ok=True)
            
        for i in range(1, 4):  # Creates folders for Season 1, 2, and 3
            season_folder = os.path.join(main_destination_folder, f"Season {i}")
            print(f"Creating season folder: {season_folder}")
            if not DRY_RUN:
                os.makedirs(season_folder, exist_ok=True)
    except OSError as e:
        print(f"Error creating directories: {e}")
        return # Stop the script if we can't create folders

    # --- Step 2: Scan files and move them ---
    # Define the pattern to extract season, episode, and title from the filename
    # Example: Just The Ten Of Us [S01 E01] Move It Or Lose It (VO)
    # Group 1: Season Number (01)
    # Group 2: Episode Title (Move It Or Lose It)
    file_pattern = re.compile(r"Just The Ten Of Us \[S(\d{2}) E\d{2}\]\s(.*?)\s\(VO\)", re.IGNORECASE)

    files_moved = 0
    # List all files in the source directory
    for filename in os.listdir(SOURCE_DIRECTORY):
        # Check if the current item is a file and matches our show's name
        source_path = os.path.join(SOURCE_DIRECTORY, filename)
        if os.path.isfile(source_path) and filename.lower().startswith("just the ten of us"):
            
            match = file_pattern.match(filename)
            
            if match:
                # Extract information from the filename
                season_num_str = match.group(1) # e.g., "01", "02"
                episode_title = match.group(2).strip() # e.g., "Move It Or Lose It"
                
                # Get the file extension (e.g., .mkv, .mp4)
                file_extension = os.path.splitext(filename)[1]
                
                # Create the new filename
                new_filename = f"{episode_title}{file_extension}"
                
                # Determine the destination folder
                # int(season_num_str) converts "01" to 1
                destination_season_folder = os.path.join(main_destination_folder, f"Season {int(season_num_str)}")
                
                # Create the full final path for the file
                destination_path = os.path.join(destination_season_folder, new_filename)
                
                print(f"\nFound file: {filename}")
                print(f"  - New Name: {new_filename}")
                print(f"  - Moving to: {destination_season_folder}")

                # Move the file
                if not DRY_RUN:
                    try:
                        shutil.move(source_path, destination_path)
                        files_moved += 1
                    except Exception as e:
                        print(f"  - !!! ERROR: Could not move file. Reason: {e}")
                else:
                    print("  - [Dry Run] Move operation skipped.")

    print("\n-------------------------------------")
    if DRY_RUN:
        print("Dry run complete. Review the output above to ensure it's correct.")
        print("To move the files, change DRY_RUN to False at the top of the script.")
    else:
        print(f"Organization complete! Moved {files_moved} files.")
    print("-------------------------------------")


# --- Run the main function ---
if __name__ == "__main__":
    organize_tv_show()