"""
CareMate v4 - Main Entry Point
Healthcare AI Assistant with Emergency Detection and Intent Routing
"""

import asyncio
import sys
import os

# Add caremate_v4 to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'caremate_v4'))

from caremate_v4.backend import app
from caremate_v4.test_complete_system import main as test_main


def main():
    """Main entry point for CareMate v4"""
    
    print("🏥 CareMate v4 - Healthcare AI Assistant")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            print("Running system tests...")
            asyncio.run(test_main())
            
        elif command == "server":
            print("Starting FastAPI server...")
            import uvicorn
            uvicorn.run(app, host="0.0.0.0", port=8000)
            
        else:
            print(f"Unknown command: {command}")
            print("Available commands: test, server")
    else:
        print("Usage:")
        print("  python main.py test    - Run system tests")
        print("  python main.py server  - Start API server")


if __name__ == "__main__":
    main()
