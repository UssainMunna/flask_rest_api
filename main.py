from flask import Flask,request
from flask_pymongo import pymongo
from flask import jsonify 
from flask_jwt_extended import JWTManager, create_access_token,get_jwt_identity,jwt_required
from bson import ObjectId

app = Flask(__name__)
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.config["JWT_SECRET_KEY"] = "hbh84ytvn4u5hb56un"

jwt = JWTManager(app)

def connect_to_mongo():
    client = pymongo.MongoClient(app.config["MONGO_URI"])
    return client['user_data']


@app.route("/register", methods=["POST"])
def register():
    user_data = request.json
    db = connect_to_mongo()
    collection = db["users"]
    
    # Validate required fields
    required_fields = ["first_name", "last_name", "email", "password"]
    missing_fields = [field for field in required_fields if field not in user_data]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    # Validate unique username/email
    existing_user = collection.find_one({"email": user_data["email"]})
    if existing_user:
        return jsonify({"error": "Email already exists."}), 400

    # Insert new user
    new_user = {
        "first_name": user_data["first_name"],
        "last_name": user_data["last_name"],
        "email": user_data["email"],
        "password": user_data["password"]
    }
    result = collection.insert_one(new_user)
    return jsonify({"message": "User registered successfully.", "user_id": str(result.inserted_id)})


@app.route("/login", methods=["POST"])
def login():
    user_data = request.json
    db = connect_to_mongo()
    collection = db["users"]
    
    #Validate required fields
    required_fields = ["email", "password"]
    missing_fields = [field for field in required_fields if field not in user_data]
    if missing_fields:return jsonify({"error": f"Username and Password are required: {', '.join(missing_fields)}"}), 400

    #Validate user exist
    existing_user = collection.find_one({"email": user_data["email"]})
    print(existing_user)
    if existing_user:
        access_token = create_access_token(identity=existing_user['email'])
        return jsonify({"access_token": access_token}), 200
    else:return jsonify({"error": "Invalid Credentials"}), 400


@app.route("/template", methods=["POST"])
@jwt_required()
def insert_template():
    db = connect_to_mongo()
    collection = db["templates"]
    # Extract User mail using jwt identity
    user_email = get_jwt_identity()
    template_data = request.json
    # Add the user's email to the template data
    template_data["user_email"] = user_email  
    result = collection.insert_one(template_data)
    print(result)
    return jsonify({"message": "Template inserted successfully.", "template_id": str(result.inserted_id)})


@app.route("/template", methods=["GET"])
@jwt_required()
def get_all_templates():
    db = connect_to_mongo()
    collection = db["templates"]
    # Extract User mail using jwt identity
    user_email = get_jwt_identity()
    templates = collection.find({"user_email": user_email})

    template_list = []
    for template in templates:
        template["_id"] = str(template["_id"])  # Convert ObjectId to string for JSON serialization
        template_list.append(template)
    return jsonify(template_list)

@app.route("/template/<template_id>", methods=["GET"])
@jwt_required()
def get_one_templates(template_id):
    db = connect_to_mongo()
    collection = db["templates"]
    # Extract User mail using jwt identity
    user_email = get_jwt_identity()
    template = collection.find_one({"_id": ObjectId(template_id), "user_email": user_email})
    if template:
        template["_id"] = str(template["_id"])  # Convert ObjectId to string for JSON serialization
        return jsonify(template)
    else:
        return jsonify({"message": "Template not found."}), 404


@app.route("/template/<template_id>", methods=["PUT"])
@jwt_required()
def update_template(template_id):
    db = connect_to_mongo()
    collection = db["templates"]
    # Extract User mail using jwt identity
    user_email = get_jwt_identity()
    template = collection.find_one({"_id": ObjectId(template_id), "user_email": user_email})
    if template:
        template_data = request.json
        collection.update_one(
            {"_id": ObjectId(template_id), "user_email": user_email},
            {"$set": template_data}
        )
        
        return jsonify({"message": "Template updated successfully."})
    else:
        return jsonify({"message": "Template not found."}), 404
    
@app.route("/template/<template_id>", methods=["DELETE"])
@jwt_required()
def delete_template(template_id):
    db = connect_to_mongo()
    collection = db["templates"]
    # Extract User mail using jwt identity
    user_email = get_jwt_identity()
    result = collection.delete_one(
        {"_id": ObjectId(template_id), "user_email": user_email})
    if result.deleted_count ==1:return jsonify({"message": "Template deleted successfully."})
    else:return jsonify({"message": "Template not found."}), 404

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
    
    