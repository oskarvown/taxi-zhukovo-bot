#!/usr/bin/env python
"""
Verify that all new v1.1 modules can be imported correctly
Run from project root: python verify_imports.py
"""
import sys
from pathlib import Path

# Ensure we're running from project root
root = Path(__file__).parent
sys.path.insert(0, str(root))

print("Verifying v1.1 module imports...")
print("=" * 60)

try:
    print("✓ bot.handlers.auth")
    from bot.handlers.auth import phone_auth_start
    
    print("✓ bot.handlers.user_intercity")
    from bot.handlers.user_intercity import intercity_info_command
    
    print("✓ bot.handlers.driver_intercity")
    from bot.handlers.driver_intercity import intercity_reply_callback
    
    print("✓ bot.middlewares.ban_guard")
    from bot.middlewares.ban_guard import BanGuardMiddleware
    
    print("✓ bot.services.user_penalty_service")
    from bot.services.user_penalty_service import UserPenaltyService
    
    print("✓ Updated models")
    from bot.models import User, Order, OrderTariff
    
    print("=" * 60)
    print("✅ All v1.1 modules imported successfully!")
    print("\nNext steps:")
    print("1. Run migration: python database/migrations/add_phone_auth_and_intercity.py")
    print("2. Start bot: python run.py")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nMake sure you're running from the project root directory.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

