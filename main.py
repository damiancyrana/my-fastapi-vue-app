# main.py

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import pandas as pd
import plotly.express as px
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Inicjalizacja aplikacji FastAPI
app = FastAPI()

# Konfiguracja CORS (jeśli frontend działa na innym porcie)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Możesz tu wpisać adres frontend-u
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Definicja modeli Pydantic
class Transaction(BaseModel):
    transaction_number: int
    starting_balance: float
    invested_capital: float
    profit: float

class SimulationRequest(BaseModel):
    transactions: List[Transaction]
    target_amount: float

# Endpoint do symulacji
@app.post("/simulate")
def simulate(simulation_request: SimulationRequest):
    # Konwersja danych transakcji do słownika
    transactions = {}
    for t in simulation_request.transactions:
        transactions[t.transaction_number] = (t.starting_balance, t.invested_capital, t.profit)

    target_amount = simulation_request.target_amount

    # Przetwarzanie transakcji
    existing_transactions_df, average_return, average_reinvestment_percent, account_balance = process_transactions(transactions)

    existing_transactions_count = len(existing_transactions_df)
    initial_balance_after_transactions = account_balance

    # Symulacja przyszłych transakcji
    simulation_df = simulate_account_value(
        initial_balance_after_transactions,
        average_return,
        target_amount,
        average_reinvestment_percent,
        existing_transactions_count
    )

    # Łączenie danych
    full_df = pd.concat([existing_transactions_df, simulation_df], ignore_index=True)

    # Tworzenie wykresu
    fig = plot_graph(full_df, target_amount)

    # Konwersja wykresu do JSON
    graph_json = fig.to_json()

    # Przygotowanie danych do odpowiedzi
    response_data = {
        "average_return": average_return,
        "average_reinvestment_percent": average_reinvestment_percent,
        "transactions": full_df.to_dict(orient='records'),
        "graph": graph_json,
        "message": f"Osiągnięto kwotę docelową {target_amount} PLN po {len(full_df)} transakcjach."
    }

    return JSONResponse(content=response_data)

# Funkcje pomocnicze
def process_transactions(transactions):
    transactions_data = []
    percentage_profits = []
    reinvestment_percents = []
    account_balance = None

    previous_profit = 0

    for transaction_number, (starting_balance, invested_capital, profit) in transactions.items():
        if account_balance is None:
            account_balance = starting_balance
        else:
            account_balance += previous_profit  # Dodajemy zysk z poprzedniej transakcji

        # Obliczanie procentu reinwestycji
        reinvestment_percent = (invested_capital / account_balance) * 100
        reinvestment_percents.append(reinvestment_percent)

        # Obliczanie procentowego zysku
        percentage_profit = (profit / invested_capital) * 100
        percentage_profits.append(percentage_profit)

        # Aktualizacja salda konta po transakcji
        account_balance += profit

        # Zapisujemy dane transakcji
        transactions_data.append({
            'Numer transakcji': transaction_number,
            'Saldo początkowe (PLN)': round(starting_balance, 2),
            'Zainwestowany kapitał (PLN)': round(invested_capital, 2),
            'Zysk (PLN)': round(profit, 2),
            'Zysk (%)': round(percentage_profit, 2),
            'Reinwestycja (%)': round(reinvestment_percent, 2),
            'Saldo konta po transakcji (PLN)': round(account_balance, 2)
        })

        previous_profit = profit

    existing_transactions_df = pd.DataFrame(transactions_data)

    average_return = sum(percentage_profits) / len(percentage_profits)
    average_reinvestment_percent = sum(reinvestment_percents) / len(reinvestment_percents)

    return existing_transactions_df, average_return, average_reinvestment_percent, account_balance

def simulate_account_value(initial_balance, average_return, target_amount, average_reinvestment_percent, existing_transactions_count=0, max_transactions=1000):
    sim_data = []
    account_balance = initial_balance
    transaction_number = existing_transactions_count

    for _ in range(max_transactions):
        transaction_number += 1
        invested_capital = account_balance * (average_reinvestment_percent / 100)
        return_amount = invested_capital * (average_return / 100)
        account_balance += return_amount

        sim_data.append({
            'Numer transakcji': transaction_number,
            'Saldo początkowe (PLN)': round(account_balance - return_amount, 2),
            'Zainwestowany kapitał (PLN)': round(invested_capital, 2),
            'Zysk (PLN)': round(return_amount, 2),
            'Zysk (%)': round(average_return, 2),
            'Reinwestycja (%)': round(average_reinvestment_percent, 2),
            'Saldo konta po transakcji (PLN)': round(account_balance, 2)
        })

        if account_balance >= target_amount:
            break
    else:
        print(f"Przekroczono maksymalną liczbę transakcji dla zwrotu {average_return}%. Zwiększ zwrot lub zmniejsz kwotę docelową")

    df = pd.DataFrame(sim_data)
    return df

def plot_graph(df, target_amount):
    # Tworzenie wykresu liniowego
    fig = px.line(
        df,
        x='Numer transakcji',
        y='Saldo konta po transakcji (PLN)',
        title='Symulator działania dźwigni 1:100',
        markers=True,
        hover_data=['Zainwestowany kapitał (PLN)', 'Zysk (PLN)', 'Zysk (%)', 'Reinwestycja (%)']
    )

    # Ustawienia linii
    fig.update_traces(line_color='purple')

    # Dodanie linii docelowej
    fig.add_hline(y=target_amount, line_dash='dash', line_color='red', annotation_text='Kwota docelowa')

    # Ustawienia osi
    fig.update_layout(
        xaxis_title='Numer transakcji',
        yaxis_title='Saldo konta (PLN)',
    )

    return fig
