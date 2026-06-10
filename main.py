from rich.console import Console
from rich.table import Table
from rich import box
from src.transactionprocessor import TransactionProcessor
from src.exchangerateutility import ExchangeRateUtility
from src.ledger import LedgerLoader

console = Console()

def get_date_range_from_transactions(transactions):
    if not transactions:
        return None, None
    dates = [t.date for t in transactions]
    return min(dates), max(dates)

def format_amount(amount):
    return f"₹{amount:,.2f}"

def print_a3_reports(reports_a3):
    console.print("\n[bold]REPORT A3 - LOT-WISE HOLDINGS[/bold]", style="cyan")
    for year in sorted(reports_a3.keys()):
        table = Table(title=f"Year: {year}", show_header=True, header_style="bold magenta", box=box.ROUNDED, show_lines=True)
        table.add_column("Lot ID", style="cyan", width=20)
        table.add_column("Invested Amount", justify="right", style="green")
        table.add_column("Peak Value", justify="right", style="green")
        table.add_column("Closing Balance", justify="right", style="green")
        table.add_column("Gross Proceeds", justify="right", style="green")

        total_invested = 0
        total_peak = 0
        total_closing = 0
        total_proceeds = 0

        for lot_id, report in reports_a3[year].items():
            table.add_row(
                lot_id,
                format_amount(report.invested_amount),
                format_amount(report.peak_value),
                format_amount(report.closing_balance),
                format_amount(report.gross_proceeds_holdings)
            )
            total_invested += report.invested_amount
            total_peak += report.peak_value
            total_closing += report.closing_balance
            total_proceeds += report.gross_proceeds_holdings

        table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]{format_amount(total_invested)}[/bold]",
            f"[bold]{format_amount(total_peak)}[/bold]",
            f"[bold]{format_amount(total_closing)}[/bold]",
            f"[bold]{format_amount(total_proceeds)}[/bold]"
        )
        console.print(table)

def print_a2_reports(reports_a2):
    console.print("\n[bold]REPORT A2 - ACCOUNT-WISE CONSOLIDATED[/bold]", style="cyan")
    for year in sorted(reports_a2.keys()):
        table = Table(title=f"Year: {year}", show_header=True, header_style="bold magenta", box=box.ROUNDED, show_lines=True)
        table.add_column("Account ID", style="cyan", width=20)
        table.add_column("Invested Amount", justify="right", style="green")
        table.add_column("Peak Value", justify="right", style="green")
        table.add_column("Closing Balance", justify="right", style="green")
        table.add_column("Gross Proceeds", justify="right", style="green")

        for account_id, report in reports_a2[year].items():
            table.add_row(
                account_id,
                format_amount(report.invested_amount),
                format_amount(report.peak_value),
                format_amount(report.closing_balance),
                format_amount(report.gross_proceeds_holdings)
            )

        console.print(table)

def print_ltcg_reports(reports_ltcg):
    console.print("\n[bold]LONG-TERM CAPITAL GAINS (>3 years)[/bold]", style="cyan")
    has_data = any(len(gains) > 0 for gains in reports_ltcg.values())
    if not has_data:
        console.print("[yellow]No long-term capital gains found.[/yellow]")
        return

    for year in sorted(reports_ltcg.keys()):
        gains = reports_ltcg[year]
        if not gains:
            continue

        table = Table(title=f"Year: {year}", show_header=True, header_style="bold magenta", box=box.ROUNDED, show_lines=True)
        table.add_column("Lot ID", style="cyan", width=15)
        table.add_column("Stock", style="yellow", width=10)
        table.add_column("Units", justify="right", width=10)
        table.add_column("Cost (INR)", justify="right", style="red")
        table.add_column("Value (INR)", justify="right", style="red")
        table.add_column("Gain (INR)", justify="right", style="green")

        total_gain = 0
        for cg in gains:
            gain_style = "green" if cg.gain >= 0 else "red"
            table.add_row(
                cg.lot_id,
                cg.stock,
                str(cg.units),
                format_amount(cg.cost_of_acquisition_inr),
                format_amount(cg.total_value_of_consideration_inr),
                f"[{gain_style}]{format_amount(cg.gain)}[/{gain_style}]"
            )
            total_gain += cg.gain

        table.add_row(
            "[bold]TOTAL[/bold]",
            "",
            "",
            "",
            "",
            f"[bold green]{format_amount(total_gain)}[/bold green]" if total_gain >= 0 else f"[bold red]{format_amount(total_gain)}[/bold red]"
        )
        console.print(table)

def print_stcg_reports(reports_stcg):
    console.print("\n[bold]SHORT-TERM CAPITAL GAINS (≤3 years)[/bold]", style="cyan")
    has_data = any(len(gains) > 0 for gains in reports_stcg.values())
    if not has_data:
        console.print("[yellow]No short-term capital gains found.[/yellow]")
        return

    for year in sorted(reports_stcg.keys()):
        gains = reports_stcg[year]
        if not gains:
            continue

        table = Table(title=f"Year: {year}", show_header=True, header_style="bold magenta", box=box.ROUNDED, show_lines=True)
        table.add_column("Lot ID", style="cyan", width=15)
        table.add_column("Stock", style="yellow", width=10)
        table.add_column("Units", justify="right", width=10)
        table.add_column("Cost (INR)", justify="right", style="red")
        table.add_column("Value (INR)", justify="right", style="red")
        table.add_column("Gain (INR)", justify="right", style="green")

        total_gain = 0
        for cg in gains:
            gain_style = "green" if cg.gain >= 0 else "red"
            table.add_row(
                cg.lot_id,
                cg.stock,
                str(cg.units),
                format_amount(cg.cost_of_acquisition_inr),
                format_amount(cg.total_value_of_consideration_inr),
                f"[{gain_style}]{format_amount(cg.gain)}[/{gain_style}]"
            )
            total_gain += cg.gain

        table.add_row(
            "[bold]TOTAL[/bold]",
            "",
            "",
            "",
            "",
            f"[bold green]{format_amount(total_gain)}[/bold green]" if total_gain >= 0 else f"[bold red]{format_amount(total_gain)}[/bold red]"
        )
        console.print(table)

def print_fy_reports(reports_fy):
    console.print("\n[bold]FINANCIAL YEAR REPORT - STOCK-WISE[/bold]", style="cyan")
    for fy_label in sorted(reports_fy.keys()):
        table = Table(title=f"FY: {fy_label}", show_header=True, header_style="bold magenta", box=box.ROUNDED, show_lines=True)
        table.add_column("Stock", style="yellow")
        table.add_column("Opening Units", justify="right")
        table.add_column("Opening Cost", justify="right", style="green")
        table.add_column("Units Acquired", justify="right")
        table.add_column("Avg Cost/Share", justify="right", style="green")
        table.add_column("Units Sold", justify="right")
        table.add_column("Total Consideration", justify="right", style="green")
        table.add_column("Closing Units", justify="right")
        table.add_column("Closing Value", justify="right", style="green")

        for stock, report in sorted(reports_fy[fy_label].items()):
            table.add_row(
                stock,
                str(report.opening_units),
                format_amount(report.opening_cost),
                str(report.units_acquired),
                format_amount(report.avg_cost_per_share_acquired),
                str(report.units_sold),
                format_amount(report.total_consideration),
                str(report.closing_units),
                format_amount(report.closing_value)
            )

        console.print(table)

if __name__ == "__main__":
    l1 = LedgerLoader("records")
    transactions = l1.get_transactions()

    start_date, end_date = get_date_range_from_transactions(transactions)
    console.print(f"[bold cyan]Date range from transactions:[/bold cyan] {start_date} to {end_date}")

    t1 = TransactionProcessor(l1.get_accounts(), transactions)
    e1 = ExchangeRateUtility()

    x, a2, fy, y, z = t1.generate_reports()

    print_a3_reports(x)
    print_a2_reports(a2)
    print_fy_reports(fy)
    print_ltcg_reports(y)
    print_stcg_reports(z)
