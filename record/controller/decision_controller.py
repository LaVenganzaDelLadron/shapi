import json
from json import JSONDecodeError
from rest_framework import status, request
from rest_framework.exceptions import UnsupportedMediaType
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from record.models import Record
from record.serializers import RecordSerializer


class Node:
    def __init__(self, key):
        self.key = key
        self.left = None
        self.right = None

class BinaryTree:
    def __init__(self, record_key):
        self.root = Node(record_key)





































