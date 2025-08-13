<?php
// 에러 리포팅 활성화 (개발용)
ini_set('display_errors', 1);
error_reporting(E_ALL);

// 로그 파일 경로 설정
define('LOG_FILE', __DIR__ . '/../logs/stock_data_fetcher.log');

function write_log($message) {
    error_log(date('[Y-m-d H:i:s]') . ' ' . $message . PHP_EOL, 3, LOG_FILE);
}

/**
 * 실시간 상승률 상위 30위 종목 데이터를 데이터베이스에서 가져옵니다.
 *
 * @param PDO $pdo 데이터베이스 연결 객체
 * @return array 주식 데이터 배열
 */
function get_top_30_rising_stocks(PDO $pdo): array
{
    write_log("get_top_30_rising_stocks 함수 시작.");

    // SQL 쿼리: 상승률 상위 30위 종목과 관련 뉴스 3개를 함께 조회합니다.
    // ROW_NUMBER()를 사용하여 각 종목별로 최신 뉴스 3개만 선택합니다.
    $sql = "
        SELECT
            t.rank, t.stock_code, t.stock_name, t.current_price, t.fluctuation_rate, t.volume, t.updated_at,
            n.title, n.link, n.pub_date, n.theme
        FROM
            top_30_rising_stocks t
        LEFT JOIN (
            SELECT
                stock_code, title, link, pub_date, theme,
                ROW_NUMBER() OVER(PARTITION BY stock_code ORDER BY pub_date DESC) as rn
            FROM
                stock_news
        ) n ON SUBSTRING_INDEX(t.stock_code, '_', 1) = n.stock_code COLLATE utf8mb4_unicode_ci AND n.rn <= 3
        WHERE t.rank > 0
        ORDER BY
            t.rank ASC, n.pub_date DESC
    ";
    write_log("SQL 쿼리 실행: " . preg_replace("/
/", " ", $sql)); // 쿼리 로깅 (줄바꿈 제거)

    try {
        // 쿼리를 실행하고 결과를 가져옵니다.
        $stmt = $pdo->query($sql);
        $results = $stmt->fetchAll(PDO::FETCH_ASSOC);
        write_log("쿼리 실행 성공. 조회된 결과 수: " . count($results));

        // 결과를 연관 배열로 변환하여 처리합니다.
        $stocks = [];
        foreach ($results as $row) {
            $stock_code = $row['stock_code'];
            if (!isset($stocks[$stock_code])) {
                $stocks[$stock_code] = [
                    'rank' => $row['rank'],
                    'stock_code' => $row['stock_code'],
                    'stock_name' => $row['stock_name'],
                    'current_price' => $row['current_price'],
                    'fluctuation_rate' => $row['fluctuation_rate'],
                    'volume' => $row['volume'],
                    'updated_at' => $row['updated_at'],
                    'news' => []
                ];
            }
            if ($row['title']) {
                $stocks[$stock_code]['news'][] = [
                    'title' => $row['title'],
                    'link' => $row['link'],
                    'theme' => $row['theme'],
                    'pub_date' => $row['pub_date']
                ];
            }
        }
        write_log("주식 데이터 처리 완료. 최종 종목 수: " . count($stocks));
        return $stocks;

    } catch (PDOException $e) {
        write_log("SQL Error in get_top_30_rising_stocks: " . $e->getMessage());
        return []; // 오류 발생 시 빈 배열 반환
    } finally {
        write_log("get_top_30_rising_stocks 함수 종료.");
    }
}
?>