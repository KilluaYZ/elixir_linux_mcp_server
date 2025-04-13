import json 
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def build_raw_resp(data=None, message="", status="unKnown") -> str:
    resp = {
        "data": data,
        "message": message,
        "status": status
    }
    return json.dumps(resp, ensure_ascii=False, indent=4, cls=DateTimeEncoder)

def build_success_resp(data=None, message="请求成功") -> str:
    return build_raw_resp(data=data, message=message, status="success")

def build_fail_resp(data=None, message="请求失败") -> str:
    return build_raw_resp(data=data, message=message, status="fail")
