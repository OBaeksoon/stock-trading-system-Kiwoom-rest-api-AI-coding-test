function updateNews() {
    document.getElementById('updateStatus').innerHTML = '<p style="color: #0056b3;">뉴스를 업데이트 중입니다. 잠시만 기다려주세요...</p>';
    
    fetch('update_news.php')
        .then(response => {
            if (!response.ok) {
                throw new Error('네트워크 응답이 올바르지 않습니다.');
            }
            return response.text();
        })
        .then(data => {
            document.getElementById('updateStatus').innerHTML = '<p style="color: green;">뉴스 업데이트가 완료되었습니다. 페이지를 새로고침하세요.</p>';
            console.log(data); // 서버 응답을 콘솔에 기록
        })
        .catch(error => {
            document.getElementById('updateStatus').innerHTML = '<p style="color: red;">업데이트 중 오류가 발생했습니다.</p>';
            console.error('Fetch Error:', error);
        });
}
