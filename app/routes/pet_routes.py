import os
import google.genai as genai
from flask import Blueprint, request, abort, make_response
from dotenv import load_dotenv
from ..db import db
from ..models.pet import Pet

load_dotenv() 

bp = Blueprint("pets", __name__, url_prefix="/pets")

@bp.post("")
def create_pet():
    request_body = request.get_json()

    try:
        species = request_body["animal"]
        personality = request_body["personality"]
        color = request_body["coloration"]
    except KeyError as error:
        response = {"message": f"Invalid request: missing {error.args[0]}"}
        abort(make_response(response, 400))

    try:
        name = generate_pet_name(species, color, personality)
    except Exception as e:
        abort(make_response({"message": f"AI name generation failed: {str(e)}"}, 500))

    request_body["name"] = name

    try:
        new_pet = Pet.from_dict(request_body)
    except KeyError as error:
        response = {"message": f"Invalid data: missing {error.args[0]}"}
        abort(make_response(response, 400))

    db.session.add(new_pet)
    db.session.commit()

    return make_response(new_pet.to_dict(), 201)


@bp.get("")
def get_pets():
    pet_query = db.select(Pet)

    pets = db.session.scalars(pet_query)
    response = []

    for pet in pets:
        response.append(pet.to_dict())

    return response

@bp.get("/<pet_id>")
def get_single_pet(pet_id):
    pet = validate_model(Pet,pet_id)
    return pet.to_dict()

@bp.patch("/<pet_id>")
def regenerate_pet_name(pet_id):
    pet = validate_model(Pet, pet_id)
    try:
        new_name = generate_pet_name(pet.animal_type, pet.color, pet.personality)
        pet.name = new_name
        db.session.commit()
    except Exception as e:
        abort(make_response({"message": f"Failed to regenerate name: {str(e)}"}, 500))

    return "", 204

def generate_pet_name(species, color, personality):
    prompt = (
        f"Suggest a creative, unique, and cute name for a {color} {species} "
        f"with a {personality} personality. Only return a single-word name, nothing else."
    )

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)

    return response.text.strip().split('\n')[0]

def validate_model(cls,id):
    try:
        id = int(id)
    except:
        response =  response = {"message": f"{cls.__name__} {id} invalid"}
        abort(make_response(response , 400))

    query = db.select(cls).where(cls.id == id)
    model = db.session.scalar(query)
    if model:
        return model

    response = {"message": f"{cls.__name__} {id} not found"}
    abort(make_response(response, 404))