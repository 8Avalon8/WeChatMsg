import os
from app.DataBase import msg_db, micro_msg_db
from app.person_lite import Contact
from app.util.exporter.exporter_txt import TxtExporter
from app.util.exporter.exporter_json import JsonExporter
from app.util.exporter.exporter_html import HtmlExporter
from app.util.exporter.exporter_csv import CSVExporter
from app.util.exporter.simple_txt_exporter import SimpleTxtExporter
import json

def convert_to_timestamp(time_input) -> int:
    """
    将输入的时间转换为时间戳
    支持时间戳、字符串、date对象等多种输入格式
    :param time_input: 输入的时间（支持时间戳、'YYYY-MM-DD HH:MM:SS'格式字符串、date对象）
    :return: 时间戳（整数）
    """
    from datetime import datetime, date
    
    if isinstance(time_input, (int, float)):
        # 如果输入是时间戳，直接返回
        return int(time_input)
    elif isinstance(time_input, str):
        # 如果输入是格式化的时间字符串，将其转换为时间戳
        try:
            dt_object = datetime.strptime(time_input, '%Y-%m-%d %H:%M:%S')
            return int(dt_object.timestamp())
        except ValueError:
            # 如果转换失败，尝试其他常见格式
            try:
                dt_object = datetime.strptime(time_input, '%Y-%m-%d')
                return int(dt_object.timestamp())
            except ValueError:
                raise ValueError("Unsupported date format. Please use 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'")
    elif isinstance(time_input, date):
        # 如果输入是datetime.date对象，将其转换为时间戳
        dt_object = datetime.combine(time_input, datetime.min.time())
        return int(dt_object.timestamp())
    else:
        raise ValueError("Unsupported input type. Must be timestamp, string or date object")

def get_chatroom_list():
    """
    获取所有群组信息
    返回格式: [(群名称, 群ID), ...]
    """
    # 确保数据库已初始化
    micro_msg_db.init_database()
    
    try:
        sql = '''
            SELECT ChatRoomName, RoomData
            FROM ChatRoom 
            WHERE ChatRoomName IS NOT NULL 
            ORDER BY ChatRoomName
        '''
        micro_msg_db.cursor.execute(sql)
        chatrooms = micro_msg_db.cursor.fetchall()
    except Exception as e:
        print(f"Error querying database: {e}")
        return []
    
    result = []
    for chatroom in chatrooms:
        room_id = chatroom[0]    # 群ID
        room_data = chatroom[1]  # 群名称数据
        
        try:
            from app.DataBase.hard_link import decodeRoomData
            decoded_data = decodeRoomData(room_data)
            room_name = decoded_data.get('name', room_id)
        except:
            room_name = room_id
                
        result.append((room_name, room_id))
    
    return result

def export_chat_history(chatroom_id: str, export_path: str, export_format: str = "txt", message_types: dict = None, time_range: tuple = None):
    """
    导出指定群组的聊天记录
    :param chatroom_id: 群组ID
    :param export_path: 导出路径
    :param export_format: 导出格式(txt/json/html/csv)
    :param message_types: 要导出的消息类型，默认只导出文本和系统消息
    :param time_range: 时间范围元组 (start_time, end_time)，支持时间戳、'YYYY-MM-DD HH:MM:SS'格式字符串、date对象
    """
    # 默认消息类型设置
    if message_types is None:
        message_types = {
            1: True,      # 文本
            3: False,     # 图片
            34: False,    # 语音
            43: False,    # 视频
            47: False,    # 表情
            49: False,    # 文件和链接
            10000: True   # 系统消息
        }

    # 1. 关闭现有连接并重新初始化数据库
    msg_db.close()
    micro_msg_db.close()
    msg_db.init_database()
    micro_msg_db.init_database()
    
    if not msg_db.open_flag:
        raise Exception("Database not exists or decrypt failed")

    # 2. 获取群组信息
    chatroom_info = micro_msg_db.get_chatroom_info(chatroom_id)
    if not chatroom_info:
        raise Exception(f"Chatroom {chatroom_id} not found")
    
    # 3. 创建Contact对象
    contact_info = {
        'UserName': chatroom_id,
        'Type': 2,  # 群聊类型
        'Remark': chatroom_info[0],  # 群名称
        'NickName': chatroom_info[0]
    }
    contact = Contact(contact_info)

    # 4. 创建导出目录
    export_dir = os.path.join(export_path, '聊天记录', contact.remark)
    os.makedirs(export_dir, exist_ok=True)

    # 5. 根据格式选择导出器
    exporters = {
        "txt": TxtExporter,
        "json": JsonExporter,
        "html": HtmlExporter,
        "csv": CSVExporter
    }
    
    if export_format not in exporters:
        raise ValueError(f"Unsupported format: {export_format}")
        
    exporter_class = exporters[export_format]
    exporter = exporter_class(contact, message_types=message_types)

    # 6. 构建SQL查询获取消息
    sql_messages = '''
        SELECT 
            m.localId,             -- 0
            m.TalkerId,           -- 1
            m.Type,               -- 2
            m.SubType,            -- 3
            m.IsSender,           -- 4
            m.CreateTime,         -- 5
            m.Status,             -- 6
            m.StrContent,         -- 7
            strftime('%Y-%m-%d %H:%M:%S', m.CreateTime, 'unixepoch', 'localtime') as StrTime,  -- 8
            m.MsgSvrID,           -- 9
            m.BytesExtra,         -- 10
            m.CompressContent,    -- 11
            m.DisplayContent      -- 12
        FROM MSG m
        WHERE m.StrTalker=?
    '''
    params = [chatroom_id]

    # 添加时间范围过滤
    if time_range:
        try:
            start_time = convert_to_timestamp(time_range[0]) if time_range[0] else None
            end_time = convert_to_timestamp(time_range[1]) if time_range[1] else None
            
            if start_time is not None:
                sql_messages += ' AND m.CreateTime >= ?'
                params.append(start_time)
            if end_time is not None:
                sql_messages += ' AND m.CreateTime <= ?'
                params.append(end_time)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid time range format: {str(e)}")

    sql_messages += ' ORDER BY m.CreateTime'
    
    # 7. 执行查询获取消息
    try:
        msg_db.cursor.execute(sql_messages, params)
        messages = msg_db.cursor.fetchall()
        
        # 8. 处理发送者信息
        processed_messages = []
        for msg in messages:
            if not msg[4] and msg[10]:  # 如果不是自己发送的且有BytesExtra
                try:
                    # 从BytesExtra中解析发送者wxid
                    from app.util.protocbuf.msg_pb2 import MessageBytesExtra
                    msgbytes = MessageBytesExtra()
                    msgbytes.ParseFromString(msg[10])
                    sender_wxid = None
                    for tmp in msgbytes.message2:
                        if tmp.field1 == 1:
                            sender_wxid = tmp.field2
                            break
                    
                    if sender_wxid:
                        # 从ChatRoom表获取群成员信息
                        sql_room = '''
                            SELECT RoomData
                            FROM ChatRoom 
                            WHERE ChatRoomName=?
                        '''
                        micro_msg_db.cursor.execute(sql_room, [chatroom_id])
                        room_info = micro_msg_db.cursor.fetchone()
                        
                        room_display_name = ''
                        if room_info and room_info[0]:
                            try:
                                from app.util.protocbuf.roomdata_pb2 import ChatRoomData
                                room_data = ChatRoomData()
                                room_data.ParseFromString(room_info[0])
                                # 在members中查找对应wxid的群昵称
                                for member in room_data.members:
                                    if member.wxID == sender_wxid:
                                        room_display_name = member.displayName if member.displayName else ''
                                        break
                            except Exception as e:
                                print(f"Error decoding room data: {e}")
                        
                        # 从Contact表获取用户基本信息
                        sql_contact = '''
                            SELECT UserName, Remark, NickName, Alias
                            FROM Contact 
                            WHERE UserName=?
                        '''
                        micro_msg_db.cursor.execute(sql_contact, [sender_wxid])
                        contact_info = micro_msg_db.cursor.fetchone()
                        
                        if contact_info:
                            sender_info = {
                                'wxid': contact_info[0],
                                'remark': contact_info[1] or '',
                                'nickname': contact_info[2] or '',
                                'alias': contact_info[3] or '',
                                'room_display_name': room_display_name
                            }
                            # 将消息元组转换为列表以便修改
                            msg_list = list(msg)
                            msg_list.append(json.dumps(sender_info))
                            processed_messages.append(tuple(msg_list))
                            continue
                except Exception as e:
                    print(f"Error processing sender info: {e}")
            
            # 如果上面的处理失败或不需要处理，直接添加原消息和空的发送者信息
            msg_list = list(msg)
            msg_list.append(None)
            processed_messages.append(tuple(msg_list))

    except Exception as e:
        raise Exception(f"Error querying messages: {e}")
    finally:
        # 9. 关闭数据库连接
        msg_db.close()
        micro_msg_db.close()

    # 10. 执行导出
    print(f"开始导出 {export_format.upper()} 格式聊天记录: {contact.remark}")
    if time_range:
        time_desc = f" ({time_range[0]} 至 {time_range[1]})" if all(time_range) else \
                   f" (从 {time_range[0]})" if time_range[0] else \
                   f" (至 {time_range[1]})"
        print(f"时间范围:{time_desc}")
    
    exporter = SimpleTxtExporter(contact, message_types=message_types)
    exporter.export(processed_messages)
    print(f"导出完成，文件保存在: {export_dir}")
    print(f"共导出 {len(processed_messages)} 条消息")

    return export_dir

if __name__ == "__main__":
    # 获取所有群组列表
    chatrooms = get_chatroom_list()
    
    # 示例：导出指定时间范围的聊天记录
    group_id = "38975636858@chatroom"  # 印悦府业主群
    export_chat_history(
        chatroom_id=group_id,
        export_path="./output",
        export_format="txt",
        time_range=("2025-01-05", "2025-01-06")  # 导出2024年1月的聊天记录
    )
