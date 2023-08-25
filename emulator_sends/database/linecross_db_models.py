from mongoengine import Document, EmbeddedDocument, DateTimeField, IntField, EmbeddedDocumentField, EmbeddedDocumentListField, DoesNotExist, Q, BooleanField
from mongoengine.errors import ValidationError, OperationError
from pymongo import UpdateOne
from datetime import datetime, timedelta
from database.db_models import MongoConnectionManager




class LineCrossInfo(EmbeddedDocument):
    line_id = IntField()
    direction = IntField()
    update_time = DateTimeField()
    flag_sending = IntField(default=0)
    
    def __eq__(self, other):
        return self.line_id == other.line_id and self.direction == other.direction
    
    def to_dict(self):
        line_json = {
            "line_id": self.line_id,
            "direction": self.direction,
            "update_time": self.update_time.strftime('%Y-%m-%d %H:%M:%S'),
            "flag_sending": self.flag_sending
        }
        return line_json
class AgcInfo(EmbeddedDocument):
    age = IntField()
    gender = IntField()
    flag_sending = IntField(default=0)

    def to_dict(self):
        agc_json = {
            "age": self.age,
            "gender": self.gender,
            "flag_sending": self.flag_sending
        }
        return agc_json

class Summary(Document):
    camera_id = IntField()
    pid = IntField()
    lines = EmbeddedDocumentListField(LineCrossInfo, default=[])
    agc = EmbeddedDocumentField(AgcInfo, default=None)
    last_time = DateTimeField(default=datetime.utcnow)
    agc_status = IntField(default=0)
    line_status = IntField(default=0)
    is_child = BooleanField(default=False)
    meta = {
        'db_alias': 'default',
        'collection': 'summary',
        'indexes': [
            {'fields': ['camera_id', 'pid'], 'unique': True},
            {'fields': ['last_time'], 'expireAfterSeconds': 24*3600}  # TTL in seconds
        ]
    }

    def to_dict(self):
        serialized_data = {
            "camera_id": self.camera_id,
            "pid": self.pid,
            "lines": [line.to_dict() for line in self.lines if line.flag_sending == 0],
            "agc": self.agc.to_dict() if self.agc is not None else {},
            "last_time": self.last_time.strftime('%Y-%m-%d %H:%M:%S.%f'),
            "agc_status": self.agc_status,
            "line_status": self.line_status,
            "is_child": self.is_child
        }
        return serialized_data
    
    @classmethod
    def remove_duplicate_lines(cls, lines):
        if lines is None or len(lines) == 0:
            return None

        unique_lines = []
        for line in lines:
            if line not in unique_lines:
                unique_lines.append(line)
        return unique_lines

    @classmethod
    def save_summary(cls, camera_id, pid, lines=None, agc=None, is_child=None):
        try:
            flag_update = False
            lines = cls.remove_duplicate_lines(lines)  # Remove duplicates
            summary = cls.objects.get(camera_id=camera_id, pid=pid)
            if lines is not None:
                for new_line in lines:
                    is_existed = False
                    for existing_line in summary.lines:
                        if existing_line == new_line:
                            is_existed = True
                            break
                    if not is_existed:
                        summary.lines.append(new_line)
                        flag_update = True
            if agc is not None:
                summary.agc = agc
                flag_update = True
            if is_child is not None:
                summary.is_child = is_child
                flag_update = True
            if flag_update:
                summary.last_time = datetime.utcnow()
                summary.save()

        except DoesNotExist:
            try:
                summary = cls(camera_id=camera_id, pid=pid, lines=lines, agc=agc, is_child=is_child, last_time=datetime.utcnow())
                summary.save()
            except (ValidationError, OperationError) as e:
                return False
        except (ValidationError, OperationError) as e:
            return False
        return True

    @classmethod
    def get_list_summary(cls, camera_ids, limit=100, time_range_seconds=3600):
        try:
            current_time = datetime.utcnow()
            # query all records AFTER this time
            time_threshold = current_time - timedelta(seconds=time_range_seconds)        
            records = Summary.objects(
                Q(camera_id__in=camera_ids) & 
                Q(last_time__lt=time_threshold) &
                Q(lines__flag_sending=0)
            ).limit(limit)            
            return records
        except DoesNotExist:
            return None

    #thaind
    @classmethod
    def get_list_summary_agc(cls, camera_ids, limit=2000, time_range_seconds=600):
        try:
            current_time = datetime.utcnow()
            # query all records BEFORE this time
            time_threshold = current_time - timedelta(seconds=time_range_seconds)        
            records = Summary.objects(
                Q(camera_id__in=camera_ids) & 
                Q(last_time__lt=time_threshold) &
                Q(lines__flag_sending=0)
            ).limit(limit)            
            return records
        except DoesNotExist:
            return None
        
    @classmethod
    def get_list_summary_agc_eval(cls, camera_ids, limit=2000, time_range_seconds=0):
        try:
            current_time = datetime.utcnow()
            # query all records BEFORE this time
            time_threshold = current_time - timedelta(seconds=time_range_seconds)        
            records = Summary.objects(
                Q(camera_id__in=camera_ids) & 
                Q(last_time__lt=time_threshold)
            ).limit(limit)            
            return records
        except DoesNotExist:
            return None


    @classmethod
    def update_bulk_flag_sending(cls, list_sending_in_progress):
        bulk_operations = []

        for record in list_sending_in_progress:
            lines_update = []
            for line in record.lines:
                line.flag_sending = 1
                lines_update.append({"line_id": line.line_id, "direction": line.direction, "update_time": line.update_time, "flag_sending": 1})
            agc_update = None
            if record.agc:
                agc_update = {"age": record.agc.age, "gender": record.agc.gender, "flag_sending": 1}
            bulk_operations.append(UpdateOne({"_id": record.id}, {"$set": {"agc": agc_update, "lines": lines_update}}))
        
        cls._get_collection().bulk_write(bulk_operations)

    @classmethod
    def get_agc_info(cls, cam_id, page_number=1, page_size=100000):
        """Get a list of person information supporting pagination.

        Args:
            cam_id (str): The camera ID.
            page_number (int): The page number.
            page_size (int): The page size.

        Returns:
            list: A list of person information.
        """

        person_information_docs = cls.objects.filter(
            camera_id=cam_id
        ).skip((page_number - 1) * page_size).limit(page_size)

        return [
            {
                'cam_id': person_information_doc.camera_id,
                'pid': person_information_doc.pid,
                'age': person_information_doc.agc.age,
                'gender': person_information_doc.agc.gender,
                'last_time': person_information_doc.last_time
            }
            for person_information_doc in person_information_docs
        ]