import matplotlib.pyplot as plt
import numpy as np

# ==========================================
# 1. Entrada de Dados
# ==========================================
meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago']

partos_real = [162, 120, 206, 157, 186, 194, 179, 171]
partos_sim = [157, 148, 194, 151, 170, 182, 165, 157]

pe_real = [12, 17, 15, 24, 13, 6, 18, 12]
pe_sim = [16, 12, 16, 13, 11, 7, 9, 12]

# ==========================================
# 2. Configuração de Estilo Global (Matplotlib Puro)
# ==========================================
plt.rcParams.update({
    'font.family': 'sans-serif',       # Combina com a fonte do LaTeX
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'legend.fontsize': 11,
    'axes.axisbelow': True,       # Garante que a grade fique ATRÁS das barras
    'axes.spines.top': False,     # Remove borda superior
    'axes.spines.right': False,   # Remove borda direita
    'axes.spines.left': False,    # Remove borda esquerda para um visual mais limpo
})

# ==========================================
# 3. Definição de Paleta de Cores e Layout
# ==========================================
cor_real = "#003464" 
cor_sim = '#FFB300'  # 26A69A - verde menta

x = np.arange(len(meses))
largura = 0.38  # Largura das barras

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# ==========================================
# PAINEL A: Partos
# ==========================================
rects1_a = ax1.bar(x - largura/2, partos_real, largura, label='Real (HRTN)', 
                   color=cor_real, edgecolor='#333333', linewidth=0.8, alpha=1)
rects2_a = ax1.bar(x + largura/2, partos_sim, largura, label='Simulado (DESK)', 
                   color=cor_sim, edgecolor='#333333', linewidth=0.8, alpha=1) # , hatch='//'

ax1.set_ylabel('Volume Mensal')
ax1.set_title('(a) Validação Histórica: Partos', pad=15, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels(meses)
ax1.tick_params(axis='both', which='both', length=0) # Remove marcações dos eixos
ax1.legend(loc='lower right', frameon=True, edgecolor='#CCCCCC')

# -> CONFIGURAÇÃO DA GRADE CORRIGIDA AQUI <-
ax1.grid(axis='y', color='#E0E0E0', linestyle='--', linewidth=1)

ax1.bar_label(rects1_a, padding=3, fontsize=9, color='#333333')
ax1.bar_label(rects2_a, padding=3, fontsize=9, color='#333333')

# ==========================================
# PAINEL B: Procedimentos Especiais
# ==========================================
rects1_b = ax2.bar(x - largura/2, pe_real, largura, label='Real (HRTN)', 
                   color=cor_real, edgecolor='#333333', linewidth=0.8, alpha=1)
rects2_b = ax2.bar(x + largura/2, pe_sim, largura, label='Simulado (DESK)', 
                   color=cor_sim, edgecolor='#333333', linewidth=0.8, alpha=1) # , hatch='//'

ax2.set_ylabel('Volume Mensal')
ax2.set_title('(b) Validação Histórica: Proc. Especiais', pad=15, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(meses)
ax2.tick_params(axis='both', which='both', length=0)
ax2.legend(loc='upper right', frameon=True, edgecolor='#CCCCCC')

# -> CONFIGURAÇÃO DA GRADE CORRIGIDA AQUI <-
ax2.grid(axis='y', color='#E0E0E0', linestyle='--', linewidth=1)

ax2.bar_label(rects1_b, padding=3, fontsize=9, color='#333333')
ax2.bar_label(rects2_b, padding=3, fontsize=9, color='#333333')

# ==========================================
# 4. Ajustes Finais e Exportação
# ==========================================
plt.tight_layout(pad=3.0) 

# Salva a figura em PDF e PNG
# plt.savefig('validacao_modelo_matplotlib.pdf', format='pdf', dpi=300, bbox_inches='tight')
# plt.savefig('validacao_modelo_matplotlib.png', format='png', dpi=300, bbox_inches='tight')

print("Gráficos gerados e salvos com sucesso!")
plt.show()