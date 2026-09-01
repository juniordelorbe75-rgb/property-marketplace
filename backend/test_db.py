from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import engine
from backend.db_models.property import PropertyDB


with Session(engine) as session:

    statement = select(PropertyDB)

    properties = session.scalars(statement).all()

    print("Properties found:", len(properties))

    for property_item in properties:
        print(
            "ID:", property_item.id,
            "| Title:", property_item.title,
            "| Owner:", property_item.owner_id
        )


 #   statement = select(UserDB).where(
  #      UserDB.email == "test@example.com"
   # )

    #user = session.scalar(statement)

    #if user is None:
    #    print("User not found")
    #else:
     #   session.delete(user)
      #  session.commit()

#        print("user.deleted:")
