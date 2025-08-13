import unittest
from unittest.mock import patch, MagicMock
import configparser
import mysql.connector
import os

# 테스트 대상 모듈 임포트
from db_utils import get_db_connection

class TestDbUtils(unittest.TestCase):

    @patch('os.path.exists')
    @patch('configparser.ConfigParser')
    @patch('mysql.connector.connect')
    def test_get_db_connection_success(self, mock_connect, mock_config_parser, mock_exists):
        """성공적인 데이터베이스 연결 테스트"""
        # 모의(mock) 설정
        mock_exists.return_value = True
        
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda section, option: {
            'DB': {'HOST': 'localhost', 'USER': 'testuser', 'PASSWORD': 'password', 'DATABASE': 'testdb', 'PORT': '3306'}
        }[section][option]
        mock_config.getint.return_value = 3306
        
        # configparser.ConfigParser()가 모의 객체를 반환하도록 설정
        config_instance = mock_config_parser.return_value
        config_instance.read.return_value = True
        config_instance.get = mock_config.get
        config_instance.getint = mock_config.getint
        
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection

        # 함수 호출
        conn = get_db_connection()

        # 단언(assert)
        self.assertIsNotNone(conn)
        self.assertEqual(conn, mock_connection)
        mock_connect.assert_called_once_with(
            host='localhost',
            user='testuser',
            password='password',
            database='testdb',
            port=3306
        )

    @patch('os.path.exists')
    def test_get_db_connection_no_config_file(self, mock_exists):
        """설정 파일이 없을 때의 테스트"""
        mock_exists.return_value = False
        conn = get_db_connection()
        self.assertIsNone(conn)

    @patch('os.path.exists')
    @patch('configparser.ConfigParser')
    def test_get_db_connection_no_db_section(self, mock_config_parser, mock_exists):
        """[DB] 섹션이 없을 때의 테스트"""
        mock_exists.return_value = True
        
        mock_config = MagicMock()
        mock_config.get.side_effect = configparser.NoSectionError('DB')
        
        config_instance = mock_config_parser.return_value
        config_instance.read.return_value = True
        config_instance.get = mock_config.get

        conn = get_db_connection()
        self.assertIsNone(conn)

    @patch('os.path.exists')
    @patch('configparser.ConfigParser')
    @patch('mysql.connector.connect')
    def test_get_db_connection_db_error(self, mock_connect, mock_config_parser, mock_exists):
        """데이터베이스 연결 오류 테스트"""
        mock_exists.return_value = True
        
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda section, option: {
            'DB': {'HOST': 'localhost', 'USER': 'testuser', 'PASSWORD': 'password', 'DATABASE': 'testdb', 'PORT': '3306'}
        }[section][option]
        mock_config.getint.return_value = 3306
        
        config_instance = mock_config_parser.return_value
        config_instance.read.return_value = True
        config_instance.get = mock_config.get
        config_instance.getint = mock_config.getint
        
        mock_connect.side_effect = mysql.connector.Error("Connection failed")

        conn = get_db_connection()
        self.assertIsNone(conn)

if __name__ == '__main__':
    unittest.main()
