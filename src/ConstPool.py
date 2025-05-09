import struct
from Common import *

CONST = enum(
    Class = b'\x07',
    FieldRef = b'\x09',
    MethodRef = b'\x0a',
    InterfaceMethodRef = b'\x0b',
    String = b'\x08',
    Integer = b'\x03',
    Float = b'\x04',
    Long = b'\x05',
    Double = b'\x06',
    NameAndType = b'\x0c',
    Utf8 = b'\x01'
)

J9CONST = enum(
    INT = 0,
    STRING = 1,
    CLASS = 2,
    LONG = 3,
    REF = 4
)

class ConstPool(object):
    def __init__(self, romclass):
        self.pool = []
        self.transform = {}
        stack = []
        # self.pool.append([-1, None])
        for i, constant in enumerate(romclass.constant_pool):
            if constant.type == J9CONST.INT:
                index = len(self.pool)
                self.pool.append([CONST.Integer, constant.value])
                self.transform[i] = {'new_index': index, 'type': CONST.Integer}
            elif constant.type == J9CONST.LONG:
                index = len(self.pool)
                self.pool.append([CONST.Double, constant.value[::-1]])
                self.pool.append([-1, None])
                self.transform[i] = {'new_index': index, 'type': CONST.Double}
            elif constant.type == J9CONST.STRING:
                index = len(self.pool)
                self.pool.append([CONST.String, b''])
                stack.append((index, CONST.Utf8, struct.pack('>H', len(constant.value)) + constant.value))
                self.transform[i] = {'new_index': index, 'type': CONST.String}
            elif constant.type == J9CONST.CLASS:
                index = len(self.pool)
                self.pool.append([CONST.Class, b''])
                stack.append((index, CONST.Utf8, struct.pack('>H', len(constant.value)) + constant.value))
                self.transform[i] = {'new_index': index, 'type': CONST.Class}
            elif constant.type == J9CONST.REF:
                index = len(self.pool)
                const_type = CONST.MethodRef if constant.descriptor.find(b'(') >= 0 else CONST.FieldRef
                self.pool.append([const_type, b'', b''])
                stack.append((index, CONST.Class, struct.pack('>H', len(constant._class)) + constant._class))
                stack.append((index, CONST.NameAndType, struct.pack('>H', len(constant.name)) + constant.name,
                              struct.pack('>H', len(constant.descriptor)) + constant.descriptor))
                self.transform[i] = {'new_index': index, 'type': const_type}
        for elem in stack:
            cp_id = len(self.pool)
            if elem[1] == CONST.Utf8:
                self.pool.append([elem[1], elem[2]])
                if self.pool[elem[0]][1]:
                    self.pool[elem[0]][2] = struct.pack('>H', cp_id + 1)
                else:
                    self.pool[elem[0]][1] = struct.pack('>H', cp_id + 1)
            elif elem[1] == CONST.Class:
                self.pool.append([elem[1], b''])
                stack.append((cp_id, CONST.Utf8, elem[2]))
                self.pool[elem[0]][1] = struct.pack('>H', cp_id + 1)
            elif elem[1] == CONST.NameAndType:
                self.pool.append([elem[1], b'', b''])
                stack.append((cp_id, CONST.Utf8, elem[2]))
                stack.append((cp_id, CONST.Utf8, elem[3]))
                self.pool[elem[0]][2] = struct.pack('>H', cp_id + 1)

    def add(self, const_type, value):
        assert isinstance(value, bytes), f"Expected bytes but got {type(value)}"
        if const_type == CONST.Class:
            index = len(self.pool)
            self.pool.append([CONST.Utf8, struct.pack('>H', len(value)) + value])
            self.pool.append([CONST.Class, struct.pack('>H', index + 1)])
            return index + 2
        elif const_type == CONST.Utf8:
            index = len(self.pool)
            self.pool.append([CONST.Utf8, struct.pack('>H', len(value)) + value])
            return index + 1

    def apply_transform(self, index, type):
        self.pool[index][0] = type

    def check_transform(self, index, type=None):
        return index in self.transform and (type and self.transform[index]['type'] == b'\x06')

    def get_transform(self, index):
        return self.transform[index]

    def write(self, stream):
        stream.write_u16(len(self.pool) + 1)
        for elem in self.pool:
            if elem[0] == -1:
                continue
            stream.write_raw_bytes(elem[0])
            stream.write_raw_bytes(elem[1])
            if len(elem) > 2:
                stream.write_raw_bytes(elem[2])
