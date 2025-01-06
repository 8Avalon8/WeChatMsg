class Contact:
    def __init__(self, contact_info):
        self.wxid = contact_info.get('UserName', '')
        self.remark = contact_info.get('Remark', self.wxid)
        self.alias = contact_info.get('Alias', '')
        self.nickName = contact_info.get('NickName', '')
        self.type = contact_info.get('Type', 0)
        self.is_chatroom = self.type == 2 
        
class ExporterBase:
    def __init__(self, contact, message_types={}, time_range=None):
        self.message_types = message_types  # 导出的消息类型
        self.contact = contact  # 联系人
        self.time_range = time_range
        self.last_timestamp = 0
        
    def export(self):
        raise NotImplementedError("export method must be implemented in subclasses")

    def is_5_min(self, timestamp) -> bool:
        if abs(timestamp - self.last_timestamp) > 300:
            self.last_timestamp = timestamp
            return True
        return False

    def get_display_name(self, is_send, message):
        """获取显示名称"""
        if self.contact.is_chatroom:
            return message[13].remark or message[13].nickName
        else:
            return "我" if is_send else (self.contact.remark or self.contact.nickName)