<?php
// 뉴스 업데이트 스크립트 실행
$python_script = '/home/stock/public_html/python_modules/get_top_30_themes_news.py';
$command = 'python3 ' . escapeshellarg($python_script) . ' > /dev/null 2>&1 &';

// 백그라운드에서 실행
exec($command);

echo "뉴스 업데이트가 시작되었습니다.";
?>