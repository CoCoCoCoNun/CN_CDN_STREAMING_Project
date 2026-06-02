시뮬레이션을 위한 출력 추가

local_dns_server와 abCDN_dns_server에서 각각 index_url(도메인), manifest를 초기화하지 않는 코드 수정
=> 매 전송마다 초기화하여 탐색하도록 수정