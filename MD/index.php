<?php
// Markdown to HTML converter function
function markdown_to_html($markdown) {
    $lines = explode("\n", $markdown);
    $html = '';
    $in_list = false;

    foreach ($lines as $line) {
        $trimmed_line = trim($line);

        // Headings (e.g., ## Title, 1. Title)
        if (preg_match('/^## (.*)/', $trimmed_line, $matches)) {
            if ($in_list) { $html .= "</ul>\n"; $in_list = false; }
            $html .= '<h2>' . $matches[1] . '</h2>' . "\n";
        } elseif (preg_match('/^### (.*)/', $trimmed_line, $matches)) {
            if ($in_list) { $html .= "</ul>\n"; $in_list = false; }
            $html .= '<h3>' . $matches[1] . '</h3>' . "\n";
        } elseif (preg_match('/^# (.*)/', $trimmed_line, $matches)) {
            if ($in_list) { $html .= "</ul>\n"; $in_list = false; }
            $html .= '<h1>' . $matches[1] . '</h1>' . "\n";
        } elseif (preg_match('/^(\d+\.)\s+(.*)/', $trimmed_line, $matches)) {
            if ($in_list) { $html .= "</ul>\n"; $in_list = false; }
            $html .= '<h2>' . $matches[1] . ' ' . $matches[2] . '</h2>' . "\n";
        } elseif (preg_match('/^(\d+\.\d+\.)\s+(.*)/', $trimmed_line, $matches)) {
            if ($in_list) { $html .= "</ul>\n"; $in_list = false; }
            $html .= '<h3>' . $matches[1] . ' ' . $matches[2] . '</h3>' . "\n";
        }
        // List items (e.g., * item, - item)
        elseif (preg_match('/^[\*\-]\s+(.*)/', $trimmed_line, $matches)) {
            if (!$in_list) { $html .= "<ul>\n"; $in_list = true; }
            // Bold and code formatting
            $li_content = preg_replace('/\*\*(.*?)\*\*/', '<strong>$1</strong>', $matches[1]);
            $li_content = preg_replace('/`(.*?)`/', '<code>$1</code>', $li_content);
            $html .= '<li>' . $li_content . '</li>' . "\n";
        }
        // Paragraphs
        else {
            if ($in_list) { $html .= "</ul>\n"; $in_list = false; }
            if ($trimmed_line !== '') {
                // Bold and code formatting
                $p_content = preg_replace('/\*\*(.*?)\*\*/', '<strong>$1</strong>', $trimmed_line);
                $p_content = preg_replace('/`(.*?)`/', '<code>$1</code>', $p_content);
                $html .= '<p>' . $p_content . '</p>' . "\n";
            } else {
                // Preserve empty lines as paragraph breaks
                $html .= '<p>&nbsp;</p>';
            }
        }
    }

    if ($in_list) { $html .= "</ul>\n"; }
    return $html;
}

$file_path = 'md_documents/GEMINI.md';
$page_title = '주식 자동매매 시스템 프로젝트';
$content = '<h1>오류</h1><p>md_documents/GEMINI.md 파일을 찾을 수 없습니다.</p>';

if (file_exists($file_path)) {
    $markdown_content = file_get_contents($file_path);
    // Set the first line as H1
    $first_line_pos = strpos($markdown_content, "\n");
    $first_line = substr($markdown_content, 0, $first_line_pos);
    $other_content = substr($markdown_content, $first_line_pos + 1);
    
    $content = '<h1>' . htmlspecialchars($first_line) . '</h1>' . markdown_to_html(htmlspecialchars($other_content));
}

?>
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo htmlspecialchars($page_title); ?></title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.7;
            color: #34495e;
            background-color: #f8f9fa;
            margin: 0;
            padding: 0; /* Changed from 20px to 0 */
        }
        .navbar {
            background-color: #2c3e50;
            padding: 15px 20px;
            color: white;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .navbar a {
            color: white;
            text-decoration: none;
            margin: 0 15px;
            font-weight: 500;
            transition: color 0.3s ease;
        }
        .navbar a:hover {
            color: #3498db;
        }
        .container {
            max-width: 900px;
            margin: 20px auto;
            background-color: #ffffff;
            padding: 30px 50px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border: 1px solid #e9ecef;
        }
        h1, h2, h3 {
            color: #2c3e50;
            font-weight: 600;
        }
        h1 {
            font-size: 2.2em;
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 3px solid #3498db;
        }
        h2 {
            font-size: 1.8em;
            margin-top: 40px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #bdc3c7;
        }
        h3 {
            font-size: 1.4em;
            margin-top: 30px;
            margin-bottom: 15px;
            color: #3498db;
        }
        ul {
            padding-left: 25px;
            list-style-type: none;
        }
        li {
            margin-bottom: 12px;
            position: relative;
            padding-left: 20px;
        }
        li::before {
            content: '■';
            position: absolute;
            left: 0;
            color: #3498db;
            font-size: 0.8em;
        }
        p {
            margin-bottom: 16px;
        }
        strong {
            color: #e74c3c;
            font-weight: 600;
        }
        code {
            background-color: #eef0f1;
            padding: 3px 6px;
            border-radius: 5px;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
            font-size: 0.95em;
            border: 1px solid #dce0e2;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <a href="index.php">프로젝트 개요</a>
        <a href="api_info.php">API 정보</a>
        <a href="updates.php">업데이트중</a>
    </div>
    <div class="container">
        <?php echo $content; ?>
    </div>
</body>
</html>
