from sqlalchemy import select
from app.database import SessionLocal
from app.models.category import Category
DEFAULT=[("Mobile Phone","Mobile phones and smartphones"),("Laptop","Laptops and notebook computers"),("Wallet","Wallets, purses and card holders"),("Bag","Backpacks, handbags and laptop bags"),("Keys","House, vehicle, locker and office keys"),("Identification Document","Identity cards and official documents"),("Jewellery","Jewellery and personal accessories"),("Electronic Accessory","Chargers, earphones, watches and accessories"),("Book","Books, notebooks and study materials"),("Clothing","Clothing and wearable items"),("Other","Items not covered by another category")]
def seed():
    with SessionLocal() as db:
        existing=set(db.scalars(select(Category.name)).all());items=[Category(name=n,description=d) for n,d in DEFAULT if n not in existing];db.add_all(items);db.commit();print(f"Inserted {len(items)} categories.")
if __name__=="__main__":seed()
