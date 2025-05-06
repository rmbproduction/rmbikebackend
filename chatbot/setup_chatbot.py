#!/usr/bin/env python
"""
Setup script to initialize and train the Rasa chatbot
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import time

def print_bike_logo():
    """Display a bike shop logo in ASCII art"""
    logo = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🚲 REPAIR MY BIKE - INTELLIGENT CHATBOT SETUP 🚲       ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    
       o__         __o        ,__o        __o           
     _`\<,_       _`\<,_     _`\<,_      _`\<,_         
    (_)/ (_)     (_)/ (_)   (_)/ (_)    (_)/ (_)        
                                                        
    """
    print(logo)
    time.sleep(1)

def check_rasa_installation():
    """Check if Rasa is installed"""
    try:
        import rasa
        print(f"✓ Rasa is installed (version {rasa.__version__})")
        return True
    except ImportError:
        print("✗ Rasa is not installed. Installing required packages...")
        return False

def install_requirements():
    """Install required packages for Rasa"""
    requirements_file = Path(__file__).parent / "requirements-rasa.txt"
    
    if not requirements_file.exists():
        print(f"✗ Requirements file not found at {requirements_file}")
        return False
    
    try:
        print("📦 Installing required packages (this may take a few minutes)...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            check=True
        )
        print("✓ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install requirements: {e}")
        return False

def setup_directories():
    """Set up required directories for Rasa"""
    base_dir = Path(__file__).parent
    
    # Create necessary directories
    dirs = [
        base_dir / "data",
        base_dir / "models",
        base_dir / ".rasa"
    ]
    
    for directory in dirs:
        directory.mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory.name}/")
    
    # Ensure NLU, stories, and rules files are in the right place
    data_dir = base_dir / "data"
    
    data_files = ["nlu.yml", "stories.yml", "rules.yml"]
    
    for file in data_files:
        source = base_dir / file
        target = data_dir / file
        
        # If the file exists at the base but not in data/, move it
        if source.exists() and not target.exists():
            shutil.move(str(source), str(target))
            print(f"✓ Moved {file} to data/ directory")
        # If the file exists in both places, ensure data/ has the latest version
        elif source.exists() and target.exists():
            shutil.copy2(str(source), str(target))
            source.unlink()  # Remove the duplicate
            print(f"✓ Updated {file} in data/ directory")
    
    print("✓ Directory structure is properly set up")
    return True

def train_model():
    """Train the Rasa model"""
    try:
        os.chdir(Path(__file__).parent)
        print("\n🚀 Training Rasa model... (this may take several minutes)")
        print("☕ Time for a coffee break while your bike chatbot learns...")
        
        subprocess.run(["rasa", "train", "--fixed-model-name", "bike_repair_bot"], check=True)
        
        print("\n✓ Model trained successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Failed to train model: {e}")
        return False

def interactive_intro():
    """Provide an interactive intro to the chatbot setup"""
    print("\n🚲 Welcome to the Bike Repair Chatbot Setup! 🚲")
    print("\nThis script will:")
    print("  1. Install Rasa and required dependencies")
    print("  2. Set up the proper directory structure")
    print("  3. Train a conversational AI model for bike repair services")
    
    print("\nYour chatbot will be able to:")
    print("  ✅ Answer questions about bike repair services")
    print("  ✅ Handle appointment bookings and cancellations")
    print("  ✅ Provide pricing information")
    print("  ✅ Offer bike maintenance tips")
    print("  ✅ Respond to specific bike problems")
    print("  ✅ Share expertise and warranty information")
    
    while True:
        response = input("\nReady to proceed? (yes/no): ").lower().strip()
        if response in ["yes", "y"]:
            break
        elif response in ["no", "n"]:
            print("Setup cancelled. Come back when you're ready to set up your bike chatbot!")
            sys.exit(0)
        else:
            print("Please enter 'yes' or 'no'")

def main():
    """Main function to set up and train the chatbot"""
    print_bike_logo()
    interactive_intro()
    
    print("\n========== BIKE REPAIR CHATBOT SETUP ==========")
    
    # Check if Rasa is installed
    if not check_rasa_installation():
        if not install_requirements():
            print("Failed to install requirements. Please install them manually.")
            sys.exit(1)
    
    # Set up directories
    setup_directories()
    
    # Train the model
    if not train_model():
        print("Failed to train the model. Please check the error message above.")
        sys.exit(1)
    
    print("\n========== SETUP COMPLETE ==========")
    print("\n🎉 Your Bike Repair Chatbot is ready to ride! 🎉")
    print("\nTo start your chatbot server:")
    print("  $ rasa run --enable-api --cors \"*\"")
    print("\nTo test your chatbot in terminal:")
    print("  $ rasa shell")
    print("\nFor more details, refer to the README.md file.")
    print("\nHappy cycling! 🚴‍♂️💨")

if __name__ == "__main__":
    main() 