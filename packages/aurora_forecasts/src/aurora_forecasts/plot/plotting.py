# We plot the actuals toghether with the Aurora data.

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
import pandas as pd

def plot_aurora_with_actuals_month(df_system_actuals_concat, sensitivity='central'):
    """
    Plots Aurora forecast data together with actuals.
    Parameters:
    - df_system_actuals_concat: DataFrame containing both Aurora forecast data and actuals.
    - sensitivity: Sensitivity scenario to filter the data (default is 'central').
    """

    # --- Estilo global ---
    mpl.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.sans-serif": ["Lato", "DejaVu Sans", "Arial", "sans-serif"],
        "text.color": "#032C33",
        "axes.labelcolor": "#032C33",
        "axes.titlecolor": "#032C33",
        "xtick.color": "#032C33",
        "ytick.color": "#032C33",
    })

    # Filter for past years
    df = df_system_actuals_concat[
        (df_system_actuals_concat['year'] <= 2025)
        # &
        # (df_system_actuals_concat['name'].str.contains('23'))
        &
        ((df_system_actuals_concat['sensitivity'].isin([sensitivity, '-'])))
    ].copy()

    df.sort_values(by=["name", "sensitivity", "year", "month", "variable"], inplace=True)

    # Create a datetime column for plotting
    df["date"] = pd.to_datetime(
        df["year"].astype(str) + "-" 
        +
        df["month"].astype(str)
    )

    # Loop through each variable and plot separately
    for variable in df["variable"].unique():
        df_var = df[df["variable"] == variable]

        plt.figure()
        plt.figure(figsize=(15, 6))
        ax = plt.gca()

        # Plot each "name" as a separate line
        for name in df_var["name"].unique():
            df_name = df_var[df_var["name"] == name]

            # choose style depending on whether it's "actuals"
            if str(name).strip().lower() == "actuals":
                ax.plot(df_name["date"], df_name["nominal_value"],
                        color="#032C33", linewidth=2.2, label="actuals")
            else:
                ax.plot(df_name["date"], df_name["nominal_value"],
                        linestyle="--", 
                        # color="gray", 
                        linewidth=1.2, alpha=0.8, label=name)

        ax.set_title(variable)
        ax.set_xlabel("Date")
        ax.set_ylabel("Price (nominal) €/MWh")

        # Format ticks
        ax.xaxis.set_major_formatter(mpl.dates.DateFormatter("%Y-%m"))
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))

        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
