from database.db import SessionLocal
from bot.models import User, UserRole, Driver

db = SessionLocal()
try:
    user = db.query(User).filter(User.telegram_id == 6840100810).first()
    if not user:
        user = User(telegram_id=6840100810, first_name="Аскар", last_name="Курбангулов", role=UserRole.DRIVER)
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"User created: {user.full_name}")
    else:
        user.role = UserRole.DRIVER
        db.commit()
        print(f"User found: {user.full_name}")
    
    driver = db.query(Driver).filter(Driver.user_id == user.id).first()
    if not driver:
        driver = Driver(user_id=user.id, car_model="Toyota Camry", car_number="А123БВ", license_number="+79852869872", is_verified=True)
        db.add(driver)
    else:
        driver.car_model = "Toyota Camry"
        driver.car_number = "А123БВ"
        driver.license_number = "+79852869872"
        driver.is_verified = True
    
    db.commit()
    db.refresh(driver)
    
    print("SUCCESS!")
    print(f"Driver: {user.full_name}")
    print(f"Car: {driver.car_model} ({driver.car_number})")
    print(f"Rating: {driver.rating}")
    print(f"Verified: {driver.is_verified}")
    print("\nOpen bot in Telegram and press /start")
    print("You will see driver menu!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

