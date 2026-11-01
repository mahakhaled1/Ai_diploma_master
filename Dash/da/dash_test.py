import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

# قراءة الملف من المجلد الحالي
df = pd.read_csv('Dash.csv')

app = Dash(__name__)
app.title = "Sales Dashboard"

# استخراج الأعمدة الرقمية
num_cols = df.select_dtypes(include='number').columns

# تصميم الواجهة مطابق للصورة
app.layout = html.Div([
    html.H1("Sales Dashboard", style={'fontWeight': 'bold'}),
    html.Label("Select a value to show in the pie chart", style={'fontSize': '16px', 'marginBottom': '8px', 'display': 'block'}),
    dcc.Dropdown(
        id='column-dropdown',
        options=[{'label': col, 'value': col} for col in num_cols],
        value='Sales' if 'Sales' in num_cols else num_cols[0],
        clearable=True
    ),
    dcc.Graph(id='pie-chart')
], style={'padding': '20px', 'fontFamily': 'sans-serif'})


@app.callback(
    Output('pie-chart', 'figure'),
    Input('column-dropdown', 'value')
)
def update_pie(selected_col):
    if not selected_col:
        selected_col = num_cols[0]

    # تجميع البيانات حسب Area
    grouped = df.groupby('Area')[selected_col].sum().reset_index()

    # لوحة الألوان المطابقة للصورة (درجات الأحمر والدرجات المحايدة)
    custom_colors = ["#eb6410", "#9be20e", "#0aed65", "#290BEF", "#f713eb"]

    # إنشاء المخطط الدائري
    fig = px.pie(
        grouped,
        names='Area',
        values=selected_col,
        title=f"Distribution of {selected_col} by Area",
        hole=0.4,
        color_discrete_sequence=custom_colors
    )

    # ضبط العناوين ومحاذاة الرسم
    fig.update_layout(
        title_font_size=18,
        title_font_color='#333333',
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    return fig


if __name__ == "__main__":
    app.run(debug=True)