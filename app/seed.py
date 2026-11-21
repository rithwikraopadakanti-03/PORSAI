from .models import Stylist, Service

def seed(db):
    if db.query(Stylist).count():
        return
    anita = Stylist(name="Anita Rao", services_text="Haircuts and styling",
                    weekdays="Mon,Tue,Wed,Thu,Fri,Sat", start_hour=10, end_hour=14)
    rahul = Stylist(name="Rahul Shetty", services_text="Hair colour and hair spa",
                    weekdays="Tue,Thu,Sat", start_hour=16, end_hour=20)
    kavya = Stylist(name="Kavya Nair", services_text="Facials and clean-ups",
                    weekdays="Mon,Wed,Fri", start_hour=9, end_hour=13)
    db.add_all([anita, rahul, kavya]); db.flush()
    db.add_all([
        Service(name="Haircut (women)", stylist_id=anita.id, price_text="Rs 600"),
        Service(name="Haircut (men)", stylist_id=anita.id, price_text="Rs 400"),
        Service(name="Blow dry and styling", stylist_id=anita.id, price_text="Rs 500"),
        Service(name="Hair colour", stylist_id=rahul.id, price_text="From Rs 2,500; depends on hair length"),
        Service(name="Hair spa", stylist_id=rahul.id, price_text="Rs 1,200"),
        Service(name="Facial", stylist_id=kavya.id, price_text="Rs 1,500"),
        Service(name="Clean-up", stylist_id=kavya.id, price_text="Rs 800"),
    ])
    db.commit()
