#!/usr/bin/env python3
"""
Helper script for admin board setup
Generates password hash and validates configuration
"""
import sys
from pathlib import Path

def generate_password_hash():
    """Generate bcrypt hash for admin password"""
    try:
        from passlib.context import CryptContext

        password = input("Enter admin password: ")
        if not password:
            print("❌ Password cannot be empty")
            return

        confirm = input("Confirm password: ")
        if password != confirm:
            print("❌ Passwords do not match")
            return

        pwd_context = CryptContext(schemes=['bcrypt'])
        hash_result = pwd_context.hash(password)

        print("\n✅ Password hash generated successfully!")
        print("\nAdd this to your .env file:")
        print(f"ADMIN_PASSWORD_HASH={hash_result}")

    except ImportError:
        print("❌ passlib not installed. Run: pip install 'passlib[bcrypt]'")
    except Exception as e:
        print(f"❌ Error: {e}")

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        print("⚠️  .env file not found")
        print("Run: cp .env.example .env")
        return False

    required_vars = [
        "DATABASE_URL_SYNC",
        "ADMIN_USERNAME",
        "ADMIN_PASSWORD_HASH"
    ]

    with open(env_path) as f:
        content = f.read()

    missing = []
    for var in required_vars:
        if var not in content or f"{var}=" not in content:
            missing.append(var)

    if missing:
        print(f"⚠️  Missing required variables in .env: {', '.join(missing)}")
        return False

    print("✅ .env file looks good!")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required = [
        "streamlit",
        "sqlalchemy",
        "asyncpg",
        "passlib",
        "pydantic",
        "pydantic_settings"
    ]

    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"⚠️  Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False

    print("✅ All dependencies installed!")
    return True

def main():
    """Main setup helper"""
    print("=" * 60)
    print("AICallGO Admin Board - Setup Helper")
    print("=" * 60)
    print()

    print("1. Generate password hash")
    print("2. Check environment configuration")
    print("3. Check dependencies")
    print("4. Full setup check")
    print("0. Exit")
    print()

    choice = input("Select option: ")
    print()

    if choice == "1":
        generate_password_hash()
    elif choice == "2":
        check_env_file()
    elif choice == "3":
        check_dependencies()
    elif choice == "4":
        print("Running full setup check...\n")
        deps_ok = check_dependencies()
        print()
        env_ok = check_env_file()
        print()

        if deps_ok and env_ok:
            print("✅ All checks passed! Ready to run:")
            print("   streamlit run app.py")
        else:
            print("❌ Setup incomplete. Please fix the issues above.")
    elif choice == "0":
        print("Goodbye!")
    else:
        print("Invalid option")

if __name__ == "__main__":
    main()
