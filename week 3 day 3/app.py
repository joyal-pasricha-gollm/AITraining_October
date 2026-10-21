from flask import Flask, jsonify, request

app = Flask(__name__)

students = [
    {
        "id": 1,
        "name": "Rhea Kapoor",
        "course": "Python",
        "score": 82
    },
    {
        "id": 2,
        "name": "Zain Malik",
        "course": "SQL",
        "score": 76
    },
    {
        "id": 3,
        "name": "Devika Rao",
        "course": "Cloud",
        "score": 91
    }
]

@app.route("/")
def home():
    return "Student API Running"


@app.route("/students", methods=["GET"])
def get_students():
    return jsonify(students)

@app.route("/students/<int:id>", methods=["GET"])
def get_student(id):

    for student in students:
        if student["id"] == id:
            return jsonify(student)

    return jsonify({
        "message": "Student not found"
    }), 404

@app.route("/students", methods=["POST"])
def add_student():

    new_student = request.get_json()

    students.append(new_student)

    return jsonify({
        "message": "Student added successfully"
    }), 201

@app.route("/students/<int:id>", methods=["PUT"])
def update_student(id):

    updated_data = request.get_json()

    for student in students:

        if student["id"] == id:

            student["name"] = updated_data["name"]
            student["course"] = updated_data["course"]
            student["score"] = updated_data["score"]

            return jsonify({
                "message": "Student updated successfully"
            })

    return jsonify({
        "message": "Student not found"
    }), 404
@app.route("/students/<int:id>", methods=["DELETE"])
def delete_student(id):

    for student in students:

        if student["id"] == id:

            students.remove(student)

            return jsonify({
                "message": "Student deleted successfully"
            })

    return jsonify({
        "message": "Student not found"
    }), 404

if __name__ == "__main__":
    app.run(debug=True)
