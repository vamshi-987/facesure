import datetime
import json

class AuditLogger:
    def __init__(self, log_file='audit.log'):
        self.log_file = log_file

    def log(self, user_id, action, details=None, ip=None):
        entry = {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'user_id': user_id,
            'action': action,
            'details': details,
            'ip': ip
        }
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

# Global logger instance for easy import
logger = AuditLogger()
