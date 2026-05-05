import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Inserindo os dados fornecidos
dados = {
    'Cenário': ['C1', 'C2', 'C3', 'C4'],
    'Consulta': [0.8, 0.7, 1.1, 12.8],
    'Indução': [63.6, 3.4, 80.9, 74.3],
    'Parto Normal': [25.1, 16.8, 30.6, 19.3],
    'Parto Cesárea': [19.1, 14.2, 27.2, 16.3]
}

df = pd.DataFrame(dados)

# 2. Transformando os dados para o formato longo (ideal para o Seaborn)
df_melted = df.melt(id_vars='Cenário', var_name='Atividade', value_name='Tempo_Fila')

# 3. Configurações visuais acadêmicas
sns.set_theme(style="whitegrid")
plt.figure(figsize=(10, 6))

# 4. Criando o gráfico de barras agrupadas
# x='Atividade' agrupa os cenários lado a lado dentro de cada setor
ax = sns.barplot(
    data=df_melted, 
    x='Atividade', 
    y='Tempo_Fila', 
    hue='Cenário', 
    palette='viridis', # Paleta de cores com alto contraste, excelente para artigos
    edgecolor='black'
)

# 5. Customização de títulos e eixos
plt.title('Comparação dos Tempos Médios de Fila por Cenário e Atividade', fontsize=14, weight='bold')
plt.xlabel('Atividade', fontsize=12, weight='bold')
plt.ylabel('Tempo Médio de Espera (minutos)', fontsize=12, weight='bold')
plt.xticks(fontsize=11)

# Ajuste da legenda
plt.legend(title='Cenários', title_fontsize='12', fontsize='11', loc='upper right')

# 6. Adicionando os rótulos de dados (valores em cima das barras)
for container in ax.containers:
    ax.bar_label(container, fmt='%.1f', padding=3, size=10)

plt.tight_layout()

# 7. Salvando a imagem em alta resolução (300 DPI) para o documento final
# plt.savefig('comparacao_filas_cenarios.png', dpi=300)

print("Gráfico gerado e salvo como 'comparacao_filas_cenarios.png'")
plt.show()