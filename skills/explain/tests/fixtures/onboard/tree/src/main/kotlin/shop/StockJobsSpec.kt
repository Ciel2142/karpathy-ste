package shop

class StockJobsSpec {
    @Scheduled(cron = "0 0 * * * *")
    fun refresh() {}
}
