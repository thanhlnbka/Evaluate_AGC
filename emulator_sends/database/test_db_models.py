# test_db_models.py

import sys
from os.path import abspath, dirname
# Add the project root directory to the Python path
sys.path.insert(0, abspath(dirname(dirname(__file__))))

import pytest
from datetime import datetime
from database.db_models import MongoConnectionManager, PersonInformation

# Pytest fixture to set up and tear down the MongoDB connection
@pytest.fixture(autouse=True)
def setup_teardown_db():
    connection_string = "mongodb://uagc:pagc@localhost:27018/agcdb"
    MongoConnectionManager.connect_mongoengine(connection_string, "test")
    yield
    # Teardown: Remove all collections after all tests are completed
    connection = MongoConnectionManager.get_connection("test")
    database = connection.get_database("agcdb")
    for collection_name in database.list_collection_names():
        database.drop_collection(collection_name)

@pytest.fixture
def clear_collections():
    # Remove all collections before running each test
    connection = MongoConnectionManager.get_connection("test")
    database = connection.get_database("agcdb")
    for collection_name in database.list_collection_names():
        database.drop_collection(collection_name)

def test_connect_mongoengine():
    assert MongoConnectionManager.connect_mongoengine("mongodb://uagc:pagc@localhost:27018/agcdb", "default") == True

def test_get_connection():
    assert MongoConnectionManager.get_connection("default") is not None

def test_insert_person_info(clear_collections):
    # Sample data for the test
    data = []
    data.append(PersonInformation(cam_id="cam1", pid=1, age=30, gender=1, last_time=datetime.utcnow()))
    data.append(PersonInformation(cam_id="cam1", pid=1, age=30, gender=1, last_time=datetime.utcnow()))

    # Insert data into MongoDB
    assert PersonInformation.insert_person_info(data) == False

    # Retrieve data from MongoDB
    result = PersonInformation.get_person_info('cam1', 1)

    # Ensure the inserted data is retrieved correctly
    assert len(result) == 1
    assert result[0].cam_id == 'cam1'
    assert result[0].pid == 1
    assert result[0].age == 30
    assert result[0].gender == 1

def test_update_person_info(clear_collections):
    # add a person to the database
    PersonInformation.save(PersonInformation(cam_id="test_update", pid=1, age=30, gender=1, last_time=datetime.utcnow()))
    # update gender
    PersonInformation.update_person_info(cam_id="test_update", pid=1, gender=2)
    # retrieve the person
    result = PersonInformation.get_person_info('test_update', 1)
    assert len(result) == 1
    assert result[0].gender == 2

def test_is_person_exist_in_db(clear_collections):
    PersonInformation.save(PersonInformation(cam_id="test_update", pid=1, age=30, gender=1, last_time=datetime.utcnow()))
    assert PersonInformation.is_person_exist_in_db("test_update", 1) == True

def test_remove_person_info(clear_collections):
    PersonInformation.save(PersonInformation(cam_id="test_update", pid=1, age=30, gender=1, last_time=datetime.utcnow()))
    assert PersonInformation.remove_person_info("test_update", 1) == True
    assert PersonInformation.is_person_exist_in_db("test_update", 1) == False

def test_get_list_person_information(clear_collections):
    # Create 11 samples of PersonInformation
    PersonInformation.save(PersonInformation(cam_id = "cam2", pid=0, age=30, gender=1, last_time=datetime.utcnow()))
    for i in range(10):
        PersonInformation.save(PersonInformation(cam_id = "cam1", pid=i+1, age=30, gender=1, last_time=datetime.utcnow()))
    # Retrieve the first page
    result = PersonInformation.get_list_person_information(cam_id="cam1", page_number=1, page_size=5)
    print("page 1")
    print(result)
    assert len(result) == 5
    assert result[0]["pid"] == 1
    assert result[4]["pid"] == 5
    # Retrieve the second page
    result = PersonInformation.get_list_person_information(cam_id="cam1", page_number=2, page_size=5)
    print("page 2")
    print(result)
    assert len(result) == 5
    assert result[0]["pid"] == 6
    assert result[4]["pid"] == 10
    # Retrieve the all data of cam2
    result = PersonInformation.get_list_person_information(cam_id="cam2", page_number=1, page_size=555)    
    assert len(result) == 1
    assert result[0]["pid"] == 0


