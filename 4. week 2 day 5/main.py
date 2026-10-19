import json
import logging
from typing import Literal, List
from pydantic import BaseModel, Field, EmailStr, ValidationError

# 12. Configure Python logging to write to registration.log (Requirement 16)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("registration.log"),
        logging.StreamHandler()  # Prints logs to terminal as well
    ]
)


# 1 & 2. Create Pydantic model with fields
class Registration(BaseModel):
    registration_id: str
    name: str
    email: EmailStr  # Automatically validates email structure
    age: int = Field(ge=18)  # 3. Validate age must be at least 18
    ticket_type: Literal["Standard", "Premium", "VIP"]  # 5. Restrict values
    amount: float = Field(gt=0)  # 4. Validate amount must be greater than 0


def process_registrations():
    # Counters for summary table
    total_records = 0
    valid_objects: List[Registration] = []
    invalid_count = 0

    # 17 & 18. File handling errors
    try:
        with open("registrations.json", "r") as file:
            raw_data = json.load(file)
    except FileNotFoundError:
        logging.error("File 'registrations.json' was not found. Execution halted.")
        print("Error: The file 'registrations.json' does not exist.")
        return
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON. 'registrations.json' contains invalid syntax.")
        print("Error: The file contains invalid JSON data formatting.")
        return

    total_records = len(raw_data)

    # 6. Load and validate each record
    for record in raw_data:
        # We temporarily extract the ID to safely reference it if Pydantic fails entirely
        reg_id = record.get("registration_id", "Unknown ID")

        try:
            # Attempt to instantiate model
            registration_obj = Registration(**record)

            # 15. Log warning if ticket type is VIP
            if registration_obj.ticket_type == "VIP":
                logging.warning(f"Registration {reg_id} registered with a VIP ticket.")

            # 13. Log successful validation
            logging.info(f"Registration {reg_id} validated successfully")
            valid_objects.append(registration_obj)

        # 8 & 14. Catch validation errors and log/print them cleanly
        except ValidationError as e:
            invalid_count += 1
            logging.error(f"Validation failed for registration {reg_id}")

            print(f"\n--- Validation Error Details [ID: {reg_id}] ---")
            for error in e.errors():
                field_name = " -> ".join(str(loc) for loc in error["loc"])
                error_msg = error["msg"]
                print(f"Registration ID: {reg_id} | Field with error: {field_name} | Error message: {error_msg}")

    # 7. Print only valid registrations
    print("\n--- Valid Registrations ---")
    for obj in valid_objects:
        print(obj)

    # Serializing demonstrations if at least one object is valid
    if valid_objects:
        sample_obj = valid_objects[0]

        # 9. Serialize Pydantic object to Python Dictionary (.model_dump() replaces .dict() in V2)
        dict_data = sample_obj.model_dump()
        print(f"\n[Serialized Dict] Type: {type(dict_data)} | Data: {dict_data}")

        # 10. Serialize Pydantic object to JSON string (.model_dump_json() replaces .json() in V2)
        json_string = sample_obj.model_dump_json()
        print(f"[Serialized JSON String] Type: {type(json_string)} | Data: {json_string}")

    # 11. Save all valid registrations into valid_registrations.json
    # Convert all valid Pydantic models back to pure lists of dicts first
    output_data = [obj.model_dump() for obj in valid_objects]
    with open("valid_registrations.json", "w") as out_file:
        json.dump(output_data, out_file, indent=4)
    logging.info("Valid records successfully exported to 'valid_registrations.json'.")

    # 20. Print Final Assessment Summary Table
    print("\n========================")
    print("   ASSESSMENT SUMMARY   ")
    print("========================")
    print(f"Total records:   {total_records}")
    print(f"Valid records:   {len(valid_objects)}")
    print(f"Invalid records: {invalid_count}")
    print("========================")


if __name__ == "__main__":
    process_registrations()
