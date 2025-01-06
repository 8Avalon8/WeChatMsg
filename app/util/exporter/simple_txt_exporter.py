import os
from datetime import datetime
import json

class SimpleTxtExporter:
    """
    简单的文本导出器
    消息字段索引说明：
    0: localId
    1: TalkerId
    2: Type
    3: SubType
    4: IsSender
    5: CreateTime
    6: Status
    7: StrContent
    8: StrTime (格式化的时间)
    9: MsgSvrID
    10: BytesExtra
    11: CompressContent
    12: DisplayContent
    13: SenderInfo (JSON格式的发送者信息，包含wxid/remark/nickname/alias)
    """
    def __init__(self, contact, message_types=None, time_range=None):
        self.contact = contact
        self.message_types = message_types or {}
        self.time_range = time_range
        self.output_dir = os.path.join(os.getcwd(), 'exported_chats')
        
    def get_display_name(self, is_send, message):
        if self.contact.is_chatroom:
            # 解析发送者信息
            sender_info = message[13]
            if sender_info:
                try:
                    sender = json.loads(sender_info)
                    # 优先使用群昵称，其次是备注名，然后是昵称，最后是微信号
                    display_name = (sender.get('room_display_name') or 
                                    sender.get('remark') or 
                                    sender.get('nickname') or 
                                    sender.get('alias') or 
                                    sender.get('wxid') or 
                                    "未知用户")
                    # 如果群昵称和备注名都不存在，且有昵称，则显示昵称
                    if (not sender.get('room_display_name') and 
                        not sender.get('remark') and 
                        sender.get('nickname')):
                        display_name = sender.get('nickname')
                except json.JSONDecodeError:
                    display_name = "未知用户"
            else:
                display_name = "未知用户"
        else:
            display_name = "我" if is_send else self.contact.remark
        return display_name

    def text(self, doc, message):
        str_content = message[7]  # StrContent
        str_time = message[8]     # StrTime
        is_send = message[4]      # IsSender
        display_name = self.get_display_name(is_send, message)
        doc.write(f'{str_time} {display_name}\n{str_content}\n\n')

    def image(self, doc, message):
        str_time = message[8]     # StrTime
        is_send = message[4]      # IsSender
        display_name = self.get_display_name(is_send, message)
        doc.write(f'{str_time} {display_name}\n[图片]\n\n')

    def audio(self, doc, message):
        str_time = message[8]     # StrTime
        is_send = message[4]      # IsSender
        display_name = self.get_display_name(is_send, message)
        doc.write(f'{str_time} {display_name}\n[语音]\n\n')

    def emoji(self, doc, message):
        str_time = message[8]     # StrTime
        is_send = message[4]      # IsSender
        display_name = self.get_display_name(is_send, message)
        doc.write(f'{str_time} {display_name}\n[表情包]\n\n')

    def file(self, doc, message):
        str_time = message[8]     # StrTime
        is_send = message[4]      # IsSender
        display_name = self.get_display_name(is_send, message)
        doc.write(f'{str_time} {display_name}\n[文件]\n\n')

    def video(self, doc, message):
        str_time = message[8]     # StrTime
        is_send = message[4]      # IsSender
        display_name = self.get_display_name(is_send, message)
        doc.write(f'{str_time} {display_name}\n[视频]\n\n')

    def system_msg(self, doc, message):
        str_content = message[7]  # StrContent
        str_time = message[8]     # StrTime
        str_content = str_content.replace('<![CDATA[', "").replace(
            ' <a href="weixin://revoke_edit_click">重新编辑</a>]]>', "")
        doc.write(f'{str_time} {str_content}\n\n')

    def music_share(self, doc, message):
        str_time = message[8]     # StrTime
        is_send = message[4]      # IsSender
        display_name = self.get_display_name(is_send, message)
        doc.write(f'{str_time} {display_name}\n[音乐分享]\n\n')

    def share_card(self, doc, message):
        str_time = message[8]     # StrTime
        is_send = message[4]      # IsSender
        display_name = self.get_display_name(is_send, message)
        doc.write(
            f'''{str_time} {display_name}
            [链接]
            标题:{message.get('title', '')}
            描述:{message.get('description', '')}
            链接:{message.get('url', '')}
            来源:{message.get('app_name', '')}
            \n\n'''
        )

    def export(self, messages):
        print(f"开始导出 TXT {self.contact.remark}")
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create output file path
        filename = os.path.join(self.output_dir, f'{self.contact.remark}.txt')
        
        with open(filename, mode='w', encoding='utf-8') as f:
            # Write header
            f.write(f"Chat History with {self.contact.remark}\n")
            f.write(f"Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Process messages
            for message in messages:
                type_ = message[2]      # Type
                sub_type = message[3]   # SubType
                
                if type_ == 1 and self.message_types.get(type_):
                    self.text(f, message)
                elif type_ == 3 and self.message_types.get(type_):
                    self.image(f, message)
                elif type_ == 34 and self.message_types.get(type_):
                    self.audio(f, message)
                elif type_ == 43 and self.message_types.get(type_):
                    self.video(f, message)
                elif type_ == 47 and self.message_types.get(type_):
                    self.emoji(f, message)
                elif type_ == 10000 and self.message_types.get(type_):
                    self.system_msg(f, message)
                elif type_ == 49:
                    if sub_type == 6 and self.message_types.get(4906):
                        self.file(f, message)
                    elif sub_type == 3 and self.message_types.get(4903):
                        self.music_share(f, message)
                    elif sub_type == 5 and self.message_types.get(4905):
                        self.share_card(f, message)
                        
        print(f"完成导出 TXT {self.contact.remark}")
        return filename 