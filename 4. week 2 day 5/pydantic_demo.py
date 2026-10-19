from pydantic import BaseModel, ValidationError, Field
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s"
)

# Pydantic model
class Employee(BaseModel):
    name: str
    age: int = Field(gt=18)
    email: str
    salary: float = Field(gt=0)


# Sample input
data = {
    "name": "Naveen",
    "age": 25,
    "email": "naveen@example.com",
    "salary": 45000
}

try:
    employee = Employee(**data)

    logging.info("Employee data validated successfully")

    print(employee)
