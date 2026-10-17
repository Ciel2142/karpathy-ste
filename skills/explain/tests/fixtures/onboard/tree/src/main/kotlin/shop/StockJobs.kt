package shop

import org.springframework.scheduling.annotation.Scheduled

class StockJobs(private val stock: StockRepository) {
    @Scheduled(cron = "0 0 * * * *")
    fun refresh() {
        stock.refreshAll()
    }
}

class StockDelegate : JavaDelegate {
    override fun execute(execution: DelegateExecution) {
        execution.setVariable("stock", "checked")
    }
}

fun main(args: Array<String>) {
    println("stock jobs")
}
