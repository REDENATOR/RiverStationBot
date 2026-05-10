from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

engine = create_engine('sqlite:///boats.db', echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    username = Column(String, nullable=True)
    full_name = Column(String)
    phone = Column(String, nullable=True)
    registered_at = Column(DateTime, default=datetime.now)


class Vessel(Base):
    __tablename__ = 'vessels'

    vessel_id = Column(Integer, primary_key=True)
    name = Column(String)
    capacity = Column(Integer)


class Route(Base):
    __tablename__ = 'routes'

    route_id = Column(Integer, primary_key=True)
    vessel_id = Column(Integer, ForeignKey('vessels.vessel_id'))
    origin = Column(String)
    destination = Column(String)
    duration = Column(Integer)
    base_price = Column(Integer)


class Schedule(Base):
    __tablename__ = 'schedules'

    schedule_id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey('routes.route_id'))
    departure_time = Column(DateTime)
    available_seats = Column(Integer)


class Ticket(Base):
    __tablename__ = 'tickets'

    ticket_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    schedule_id = Column(Integer, ForeignKey('schedules.schedule_id'))
    seat_number = Column(Integer)
    status = Column(String, default='waiting')
    price = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)

def init_db():
    Base.metadata.create_all(engine)
    print("✅ База данных готова (файл boats.db)")


# ==========================================
# ФАЙЛ: database.py
# ==========================================

def add_test_data():
    """Добавляет тестовые рейсы, чтобы было с чем работать"""
    session = Session()

    # Проверяем, есть ли уже данные
    if session.query(Route).count() > 0:
        session.close()
        return

    print("📝 Добавляем тестовые данные...")

    # 1. Создаём судно
    vessel = Vessel(name="Метеор-120", capacity=40)
    session.add(vessel)
    session.commit()

    # 2. Создаём маршруты
    route1 = Route(
        vessel_id=vessel.vessel_id,
        origin="Речной вокзал",
        destination="Зеленогорск",
        duration=45,
        base_price=450
    )
    route2 = Route(
        vessel_id=vessel.vessel_id,
        origin="Речной вокзал",
        destination="Солнечный берег",
        duration=25,
        base_price=300
    )
    session.add_all([route1, route2])
    session.commit()

    # 3. Создаём расписание на завтра (ВОТ ОТКУДА ЭТОТ КОД!)
    from datetime import timedelta
    tomorrow = datetime.now() + timedelta(days=1)

    s1 = Schedule(
        route_id=route1.route_id,
        departure_time=tomorrow.replace(hour=10, minute=0),
        available_seats=40
    )
    s2 = Schedule(
        route_id=route1.route_id,
        departure_time=tomorrow.replace(hour=12, minute=0),
        available_seats=40
    )
    s3 = Schedule(
        route_id=route2.route_id,
        departure_time=tomorrow.replace(hour=11, minute=0),
        available_seats=40
    )
    s4 = Schedule(
        route_id=route2.route_id,
        departure_time=tomorrow.replace(hour=14, minute=0),
        available_seats=40
    )

    session.add_all([s1, s2, s3, s4])
    session.commit()
    session.close()

    print("✅ Тестовые данные добавлены: 1 судно, 2 маршрута, 4 рейса")