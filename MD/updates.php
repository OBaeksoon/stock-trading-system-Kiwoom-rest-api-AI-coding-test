<?php
// Function to read work in progress content from SQLite DB
function getWorkContentFromDb() {
    $db_file = __DIR__ . '/stock_data.db';
    try {
        $pdo = new PDO('sqlite:' . $db_file);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        $stmt = $pdo->query("SELECT content FROM work_in_progress ORDER BY last_updated DESC LIMIT 1");
        $info = $stmt->fetch(PDO::FETCH_ASSOC);
        return $info ? $info['content'] : "";
    } catch (PDOException $e) {
        error_log("Database error: " . $e->getMessage());
        return "데이터베이스에서 작업 내용을 불러오는 데 실패했습니다: " . $e->getMessage();
    }
}

// Markdown to HTML converter function (simplified for this content)
function markdown_to_html($markdown) {
    $lines = explode("\n", $markdown);
    $html = '';
    $in_list = false;

    foreach ($lines as $line) {
        $trimmed_line = trim($line);

        // Headings (e.g., ## Title)
        if (preg_match('/^## (.*)/', $trimmed_line, $matches)) {
            if ($in_list) { $html .= "</ul>\n"; $in_list = false; }
            $html .= '<h2>' . htmlspecialchars($matches[1]) . '</h2>' . "\n";
        } elseif (preg_match('/^### (.*)/', $trimmed_line, $matches)) {
            if ($in_list) { $html .= "</ul>\n"; $in_list = false; }
            $html .= '<h3>' . htmlspecialchars($matches[1]) . '</h3>' . "\n";
        }
        // List items (e.g., * item, - item)
        elseif (preg_match('/^[\*\-]\s+(.*)/', $trimmed_line, $matches)) {
            if (!$in_list) { $html .= "<ul>\n"; $in_list = true; }
            $li_content = htmlspecialchars($matches[1]);
            $li_content = preg_replace('/\*\*(.*?)\*\*/', '<strong>$1</strong>', $li_content);
            $li_content = preg_replace('/`(.*?)`/', '<code>$1</code>', $li_content);
            $html .= '<li>' . $li_content . '</li>' . "\n";
        }
        // Horizontal Rule
        elseif (preg_match('/^---+\s*$/', $trimmed_line)) {
            if ($in_list) { $html .= "</ul>\n"; $in_list = false; }
            $html .= '<hr>' . "\n";
        }
        // Paragraphs
        else {
            if ($in_list) { $html .= "</ul>\n"; $in_list = false; }
            if ($trimmed_line !== '') {
                $p_content = htmlspecialchars($trimmed_line);
                $p_content = preg_replace('/\*\*(.*?)\*\*/', '<strong>$1</strong>', $p_content);
                $p_content = preg_replace('/`(.*?)`/', '<code>$1</code>', $p_content);
                $html .= '<p>' . $p_content . '</p>' . "\n";
            } else {
                $html .= '<p>&nbsp;</p>';
            }
        }
    }

    if ($in_list) { $html .= "</ul>\n"; }
    return $html;
}

$work_content_markdown = getWorkContentFromDb();
$work_content_html = markdown_to_html($work_content_markdown);

$page_title = '업데이트중';
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
            padding: 0;
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
        <h1><?php echo htmlspecialchars($page_title); ?></h1>
                <?php
        // Read the content of 20250718_작업할내용.txt
        $markdown_content = file_get_contents(__DIR__ . '/md_documents/doc/20250718_작업할내용.txt');
        if ($markdown_content === false) {
            echo "<p class=\"error\">20250718_작업할내용.txt 파일을 읽을 수 없습니다.</p>";
        } else {
            // Convert markdown to HTML and display
            echo markdown_to_html($markdown_content);
        }
        ?>

    </div>
</body>
</html>