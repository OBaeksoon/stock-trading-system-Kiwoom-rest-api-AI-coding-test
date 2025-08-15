<?php
if (!function_exists('write_log')) {
    function write_log($message) {
        if (defined('LOG_FILE')) {
            error_log(date('[Y-m-d H:i:s]') . ' ' . $message . PHP_EOL, 3, LOG_FILE);
        }
    }
}
?>