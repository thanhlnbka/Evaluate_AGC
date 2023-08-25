from mongoengine import Document, EmbeddedDocument, DateTimeField, IntField, BooleanField, ListField, FloatField, StringField, EmbeddedDocumentField, connection, connect, errors
from threading import Lock
from datetime import datetime

class MongoConnectionManager:
    _connections = {}
    _lock = Lock()

    @classmethod
    def connect_mongoengine(cls, connection_string, alias="default"):
        if alias in cls._connections:
            return cls._connections[alias]

        try:
            with cls._lock:
                if alias not in cls._connections:
                    connection = connect(alias=alias, host=connection_string, maxPoolSize=100)
                    cls._connections[alias] = connection
        except Exception as e:
            return False

        return True

    @classmethod
    def get_connection(cls, alias="default"):
        return cls._connections.get(alias, None)

class PersonInformation(Document):
    cam_id = StringField()
    pid = IntField()
    age = IntField()
    gender = IntField()
    last_time = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'db_alias': 'default',
        'collection': 'person_information',
        'indexes': [
            {'fields': ['cam_id', 'pid'], 'unique': True},
            {'fields': ['created_at'], 'expireAfterSeconds': 24 * 3600}  # TTL in seconds
        ]
    }

    @classmethod
    def get_list_person_information(cls, cam_id, page_number=1, page_size=100000):
        """Get a list of person information supporting pagination.

        Args:
            cam_id (str): The camera ID.
            page_number (int): The page number.
            page_size (int): The page size.

        Returns:
            list: A list of person information.
        """

        person_information_docs = cls.objects.filter(
            cam_id=cam_id
        ).skip((page_number - 1) * page_size).limit(page_size)

        return [
            {
                'cam_id': person_information_doc.cam_id,
                'pid': person_information_doc.pid,
                'age': person_information_doc.age,
                'gender': person_information_doc.gender,
                'last_time': person_information_doc.last_time,
                'created_at': person_information_doc.created_at,
            }
            for person_information_doc in person_information_docs
        ]

    @classmethod
    def insert_person_info(cls, person_info_list):
        try:
            cls.objects.insert(person_info_list)
            return True
        except errors.NotUniqueError as e:
            return False
        except Exception as e:
            return False

    @classmethod
    def get_person_info(cls, cam_id, pid):
        return cls.objects(cam_id=cam_id, pid=pid)

    @classmethod
    def is_person_exist_in_db(cls, cam_id, pid):
        return cls.objects(cam_id=cam_id, pid=pid).count() > 0

    # update person information
    @classmethod
    def update_person_info(cls, cam_id, pid, age=None, gender=None, last_time=None):
        try:
            person_info = cls.objects(cam_id=cam_id, pid=pid).first()

            if not person_info:
                return False

            if age is not None:
                person_info.age = age
            if gender is not None:
                person_info.gender = gender
            if last_time is not None:
                person_info.last_time = last_time

            person_info.save()
            return True

        except Exception as e:
            return False

    # delete person information
    @classmethod
    def remove_person_info(cls, cam_id, pid):
        try:
            cls.objects(cam_id=cam_id, pid=pid).delete()
            return True
        except Exception as e:
            return False

    @classmethod
    def from_dict_list(cls, dict_list):
        person_info_list = []
        for data in dict_list:
            person_info = cls(cam_id=data.get('cam_id'),
                              pid=data.get('pid'),
                              age=data.get('age'),
                              gender=data.get('gender'),
                              last_time=data.get('last_time'))
            person_info_list.append(person_info)
        return person_info_list

    
def update_agc_results_to_db(agc_results:list(dict())):
    data = []
    for r in agc_results:
        data.append(PersonInformation(cam_id=r['camid'], pid=r['pid'], age=r['age'], gender=r['gender'], last_time=r['last_time']))
    # Insert data into MongoDB
    if len(data) > 0:
        PersonInformation.insert_person_info(data) 
        
def get_agc_results_from_db(camid, pid):
    return PersonInformation.get_person_info(camid, pid)
        
