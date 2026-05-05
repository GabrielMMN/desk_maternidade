import sys
from desk.core.simulation_model import SimulationModel
from desk.config.simulation_config import SimulationConfig
from desk.core.entity import EventLogger
from desk.blocks.create_block import CreateBlock
from desk.blocks.process_block import ProcessBlock, MultiProcessBlock
from desk.blocks.decide_block import DecideBlock
from desk.blocks.dispose_block import DisposeBlock
from desk.visualization.interface import run_visualization

from desk.validation.warmup import WarmUpAnalyzer
from desk.analytics.plotting import SimulationPlotter
from desk.analytics.metrics import MetricsCollector
from desk.analytics.financial import FinancialAnalyzer
from desk.validation.stability import StabilityAnalyzer

from desk.stats.replication import ReplicationFramework

# Para o Separate Block
from desk.core.base_block import BaseBlock
from desk.core.entity import Entity

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import random





class NascimentoBlock(BaseBlock):
    """
    Bloco customizado para gerar a entidade Recém-Nascido (RN) a partir de uma Gestante.
    Bifurca o fluxo: a mãe segue para o next_block padrão, o RN segue para o next_block_rn.
    """
    def __init__(self, name, env, event_logger=None):
        super().__init__(name, env, event_logger)
        self.next_block_rn = None  # Rota exclusiva do bebê
        self.entities_created = 0  # Contador de GENERATES dos RN

    def connect_rn_to(self, next_block):
        self.next_block_rn = next_block

    def process_entity(self, mae: Entity):
        # Cria a entidade do Recém-Nascido
        rn = Entity(id=f"RN_{mae.id}", creation_time=self.env.now)
        self.entities_created += 1 # incrementa contador
        rn.priority = mae.priority # Opcional: herdar prioridade da mãe

        # Decide se o RN precisa de UCP
        decisao_ucp = random.choices([True, False], [10, 90], k=1)[0]
        rn.add_attribute('decide_ucp', decisao_ucp)

        # Cria o evento de sincronização
        evento_alta_conjunta = self.env.event()
        
        # Guarda o mesmo evento nos dois prontuários
        mae.add_attribute('evento_alta', evento_alta_conjunta)
        rn.add_attribute('evento_alta', evento_alta_conjunta)
        
        # 2. Faz a vinculação dos prontuários (para a Alta Conjunta)
        mae.add_attribute('filho', rn)
        rn.add_attribute('mae', mae)

        # Aplica os atributos (assign/modify) ao bebê
        super()._apply_attributes(rn)
        super()._modify_attributes(rn)
        
        if self.event_logger:
            self.event_logger.log_event(rn.id, self.name, self.env.now, 'create', None, details=f"Filho de {mae.id}")


        # Inicia o fluxo do Bebê de forma assíncrona
        if self.next_block_rn:
            self.env.process(self.next_block_rn.process_entity(rn))

        # A mãe continua o fluxo normal dela (yield from tranca a mãe neste fluxo)
        if self.next_block:
            yield from self.next_block.process_entity(mae)
        else:
            yield self.env.timeout(0)
# --------------------------------------

class AguardaAltaBlock(BaseBlock):
    """Bloco onde o RN entra em modo de espera até a mãe disparar o evento de alta."""
    def __init__(self, name, env, event_logger=None):
        super().__init__(name, env, event_logger)

    def process_entity(self, rn: Entity):
        evento = rn.get_attribute('evento_alta')
        
        if evento and not evento.triggered:
            if self.event_logger:
                self.event_logger.log_event(rn.id, self.name, self.env.now, 'start', None, details="Aguardando a mãe")
            
            # O bebê espera o sinal
            yield evento 
            
            if self.event_logger:
                self.event_logger.log_event(rn.id, self.name, self.env.now, 'complete', None, details="Alta Conjunta liberada")

        if self.next_block:
            yield from self.next_block.process_entity(rn)
        else:
            yield self.env.timeout(0)


class DisparaAltaBlock(BaseBlock):
    """Bloco onde a mãe aciona o evento, liberando o RN para ir embora com ela."""
    def __init__(self, name, env, event_logger=None):
        super().__init__(name, env, event_logger)

    def process_entity(self, mae: Entity):
        evento = mae.get_attribute('evento_alta')
        
        # Se o evento existe e ainda não foi disparado, a mãe o aciona
        if evento and not evento.triggered:
            evento.succeed()
            
            if self.event_logger:
                 self.event_logger.log_event(mae.id, self.name, self.env.now, 'create', None, details="Mãe assinou a alta")

        if self.next_block:
            yield from self.next_block.process_entity(mae)
        else:
            yield self.env.timeout(0)


# ================================================================
# Simulation Model
# ================================================================
def build_model(final_simulation_time=None, event_logger=None, verbose=True,
                        entity_filter=None, resource_filter=None,
                        event_type_filter=None, time_range=None):
    

    HOURS = 60    # base time: minutes
    DAYS = 1440
    YEARS = 525600

    model = SimulationModel(verbose=verbose,
        entity_filter=entity_filter,
        resource_filter=resource_filter,
        event_type_filter=event_type_filter,
        time_range=time_range)
    
    def distributions(atividade):
        return {
            'chegada' : random.expovariate(lambd= 1 / 36), # 40 por dia ; 1  cada 36 minutos
            'recepcao' : random.triangular(4, 10, 5),
            'triagem' : random.triangular(2, 10, 3),
            'consulta' : random.triangular(12, 30, 15),
            'exames_observacao' : random.triangular(120, 240, 180),
            'proc_especial' : random.triangular(30, 60, 40),
            'inducao_parto' : random.triangular(360, 1440, 720),
            'trabalho_parto' : random.triangular(360, 600, 480),   
            'parto_normal' : random.triangular(45, 75, 60),        
            'parto_cesarea' : random.triangular(75, 105, 90),      
            'pos_parto' : random.triangular(120, 240, 180),       
            'aval_inicial_rn' : random.triangular(60, 120, 90),   
            'testes_neonatais' : random.triangular(10, 20, 15),
            'internacao_ucp' : random.triangular(9000, 12000, 10560),
            'alojamento_pos_parto_normal': random.triangular(1200, 1680, 1440),
            'alojamento_pos_parto_cesarea': random.triangular(2640, 3120, 2880)
        }.get(atividade, 'error')
    
    # ============================================================
    # Create resources
    # ============================================================
    # Human resources
    recepcionista = model.add_resource('recepcionista', capacity=1, resource_type='regular')
    enf_triagem = model.add_resource('enf_triagem', capacity=1, resource_type='regular')
    med_consulta = model.add_resource('med_consulta', capacity=2, resource_type='priority')
    med_obstetra = model.add_resource('med_obstetra', capacity=1, resource_type='priority')
    med_anestesista = model.add_resource('med_anestesista', capacity=1, resource_type='priority')
    med_pediatra = model.add_resource('med_pediatra', capacity=3, resource_type='priority')

    enf_obstetra = model.add_resource('enf_obstetra', capacity=1, resource_type='priority')
    enf_neonatal = model.add_resource('enf_neonatal', capacity=2, resource_type='regular')  # TODO: regular ou priority
    tec_enf_bloco = model.add_resource('tec_enf_bloco', capacity=6, resource_type='priority')
    tec_enf_neonatal = model.add_resource('tec_enf_neonatal', capacity=16, resource_type='regular')  # original: 8

    # Infrastructure
    consultorio = model.add_resource('consultorio', capacity=2, resource_type='priority')
    leito_inducao = model.add_resource('leito_inducao', capacity=2, resource_type='priority')
    sala_parto_normal = model.add_resource('sala_parto_normal', capacity=3, resource_type='priority')
    sala_cesarea = model.add_resource('sala_cesarea', capacity=1, resource_type='priority')
    sala_proc_esp = model.add_resource('sala_proc_esp', capacity=1, resource_type='priority')

    leito_ucp = model.add_resource('leito_ucp', capacity=16, resource_type='regular')
    alojamento = model.add_resource('alojamento', capacity=25, resource_type='regular')

    # Gerador de prioridades (Classificação de Risco Obstétrico)
    def patient_severity():
        severity_dist = [15, 35, 35, 15]
        return random.choices([0, 1, 2, 3], weights=severity_dist)[0]


    # ============================================================
    # Blocks
    # ============================================================
    # Create Block
    chegadas = CreateBlock(
        'Chegadas', model.env,
        inter_arrival_time= lambda: distributions('chegada'),
        entity_prefix='Gestante',
        max_arrivals=None,
        priority_generator= patient_severity,
        event_logger=event_logger
    )

    recepcao = ProcessBlock(
        'Recepcao', model.env,
        resource=recepcionista,
        delay_time= lambda: distributions('recepcao'),
        resource_units=1,
        event_logger=event_logger
    )
    recepcao.set_resource_name('recepcionista')

    def classificar_risco():
        prioridade = random.choices([0, 1, 2, 3], [15, 35, 35, 15], k=1)[0]

        return prioridade

    triagem = ProcessBlock(
        'Triagem', model.env,
        resource=enf_triagem,
        delay_time= lambda: distributions('triagem'),
        resource_units=1,
        event_logger=event_logger
    )
    triagem.set_resource_name('enf_triagem')
    # triagem.modify_attributes(priority = lambda current: classificar_risco())


    def atualizar_status_consulta(status_atual):
            """
            Lê o estado anterior da paciente (0 se for a primeira vez),
            soma a avaliação e faz o sorteio com os pesos corretos.
            """
            # 1. Checa se é a primeira vez (se não for um dicionário, acabou de chegar)
            if not isinstance(status_atual, dict):
                n_aval = 1
            else:
                n_aval = status_atual.get('n_avaliacoes', 0) + 1

            # 2. Lógica de probabilidades dinâmicas
            if n_aval == 1:
                enc = random.choices(['A', 'B', 'C', 'D', 'E'], [70, 1, 16, 5, 8], k=1)[0]
            else:
                # Na reavaliação, o 'E' (peso 0) é matematicamente impossível
                enc = random.choices(['A', 'B', 'C', 'D', 'E'], [80, 0, 0, 20, 0], k=1)[0]

            # 3. Devolvemos um dicionário com o pacote de dados completo
            return {'n_avaliacoes': n_aval, 'encaminhamento': enc}


    consulta = MultiProcessBlock(
        'Consulta', model.env,
        resource_requirements={
            med_consulta : 1,
            consultorio : 1
        },
        delay_time= lambda: distributions('consulta'),
        event_logger=event_logger
    )
    consulta.set_resource_names({
        med_consulta : 'med_consulta',
        consultorio : 'consultorio'
    })
    consulta.modify_attributes(prontuario=lambda current: atualizar_status_consulta(current))


    tratamento = DecideBlock('Desvio', model.env, decision_type='condition', event_logger=event_logger)

    tratamento.add_route('Saida', next_block=None, condition=lambda e: e.get_attribute('prontuario', {}).get('encaminhamento') == 'A')
    tratamento.add_route('Proc_Esp', next_block=None, condition=lambda e: e.get_attribute('prontuario', {}).get('encaminhamento') == 'B')
    tratamento.add_route('Parto', next_block=None, condition=lambda e: e.get_attribute('prontuario', {}).get('encaminhamento') == 'C')
    tratamento.add_route('Internacao_ext', next_block=None, condition=lambda e: e.get_attribute('prontuario', {}).get('encaminhamento') == 'D')
    tratamento.add_route('Exames_Observacao', next_block=None, condition=lambda e: e.get_attribute('prontuario', {}).get('encaminhamento') == 'E')


    procEsp = MultiProcessBlock(
        'ProcEspecial', model.env,
        resource_requirements={
            tec_enf_bloco : 1,
            sala_proc_esp : 1
        },
        delay_time= lambda: distributions('proc_especial'),
        event_logger=event_logger
    )
    procEsp.set_resource_names({
        tec_enf_bloco : 'tec_enf_bloco',
        sala_proc_esp : 'sala_proc_esp'
    })


    # Possibilidades para o Parto
    define_parto = DecideBlock('Define_Parto', model.env, decision_type= 'probability', event_logger= event_logger)
    define_parto.add_route('Trabalho_Parto', next_block=None, probability= 0.6) 
    define_parto.add_route('Cesarea_risco', next_block=None, probability= 0.2) 
    define_parto.add_route('Inducao', next_block=None, probability= 0.2) 


    inducao = MultiProcessBlock(
        'Inducao', model.env,
        resource_requirements={
            leito_inducao : 1,
            tec_enf_bloco : 1
        },
        delay_time= lambda: distributions('inducao_parto'),
        event_logger=event_logger
    )
    inducao.set_resource_names({
        leito_inducao : 'leito_inducao',
        tec_enf_bloco : 'tec_enf_bloco'
    })


    inducao_funcionou = DecideBlock('Inducao_funcionou', model.env, decision_type= 'probability', event_logger=event_logger)
    inducao_funcionou.add_route('Sim', next_block=None, probability=0.8)  # Trabalho de Parto -> Parto Normal
    inducao_funcionou.add_route('Nao', next_block=None, probability=0.2)  # Cesárea


    trabalho_parto = ProcessBlock(
        'Trabalho_parto', model.env,
        resource=None,
        delay_time= lambda: distributions('trabalho_parto'),
        event_logger=event_logger
    )


    parto_normal = MultiProcessBlock(
        'Parto_Normal', model.env,
        resource_requirements={
            sala_parto_normal : 1,
            med_obstetra : 1,
            med_pediatra : 1,
            enf_obstetra : 1,
            tec_enf_bloco : 1,
            enf_neonatal : 1   
        },
        delay_time= lambda: distributions('parto_normal'),
        event_logger=event_logger
    )
    parto_normal.set_resource_names({
        sala_parto_normal : 'sala_parto_normal',
        med_obstetra : 'med_obstetra',
        med_pediatra : 'med_pediatra',
        enf_obstetra : 'enf_obstetra',
        tec_enf_bloco : 'tec_enf_bloco',
        enf_neonatal : 'enf_neonatal'
    })
    parto_normal.assign_attributes(tipo_parto = 'normal')


    parto_cesarea = MultiProcessBlock(
        'Parto_Cesarea', model.env,
        resource_requirements={
            sala_cesarea : 1,
            med_obstetra : 1,
            med_pediatra : 1,
            enf_obstetra : 1,
            tec_enf_bloco : 1,
            med_anestesista : 1,
            enf_neonatal : 1 
        },
        delay_time= lambda: distributions('parto_cesarea'),
        event_logger=event_logger
    )
    parto_cesarea.set_resource_names({
        sala_cesarea : 'sala_cesarea',
        med_obstetra : 'med_obstetra',
        med_pediatra : 'med_pediatra',
        enf_obstetra : 'enf_obstetra',
        tec_enf_bloco : 'tec_enf_bloco',
        med_anestesista : 'med_anestesista',
        enf_neonatal : 'enf_neonatal'
    })
    parto_cesarea.assign_attributes(tipo_parto = 'cesarea')


    pos_parto = ProcessBlock(
        'Pos_Parto', model.env,
        resource=None,
        delay_time= lambda: distributions('pos_parto'),
        event_logger=event_logger
    )


    # CreateBlock para o RN
    nascimento = NascimentoBlock('Nascimento', model.env, event_logger=event_logger)


    aval_inicial = MultiProcessBlock(
        'Aval_inicial', model.env,
        resource_requirements={
            med_pediatra : 1,
            enf_neonatal : 1
        },
        delay_time= lambda: distributions('aval_inicial_rn'),
        event_logger=event_logger
    )
    aval_inicial.set_resource_names({
        med_pediatra : 'med_pediatra',
        enf_neonatal : 'enf_neonatal'
    })
    # aval_inicial.assign_attributes(decide_ucp = lambda: random.choices([True, False], [10, 90], k=1)[0])  # atributo UCP == True or False ao RN


    precisa_ucp = DecideBlock('Precisa_UCP', model.env, decision_type='condition', event_logger=event_logger)
    precisa_ucp.add_route('Sim', next_block=None, condition= lambda rn: rn.get_attribute('decide_ucp') == True)   # UCP
    precisa_ucp.add_route('Nao', next_block=None, condition= lambda rn: rn.get_attribute('decide_ucp') == False)  # Testes Neonatais

    # Unidade de Cuidados Progressivos (UCP)
    ucp = MultiProcessBlock(
        'UCP', model.env,
        resource_requirements={
            leito_ucp : 1,
            tec_enf_neonatal : 1
        },
        delay_time= lambda: distributions('internacao_ucp'),
        event_logger=event_logger
    )
    ucp.set_resource_names({
        leito_ucp : 'leito_ucp',
        tec_enf_neonatal : 'tec_enf_neonatal'
    })


    ucp_funcionou = DecideBlock('UCP_funcionou', model.env, decision_type='probability', event_logger=event_logger)
    ucp_funcionou.add_route('Sim', next_block=None, probability=0.99)  # Alta médica após cuidados
    ucp_funcionou.add_route('Nao', next_block=None, probability=0.01)  # Óbito

    # ucp_funcionou == Nao
    obito_rn = DisposeBlock('Obito_RN', model.env, event_logger=event_logger)


    # precisa_ucp == False | Testes Neonatais (depois aguardar alta da mãe que está em Aloj_Conjunto)
    testes_neonatais = ProcessBlock('Testes_Neonatais', model.env, lambda: distributions('testes_neonatais'), tec_enf_neonatal, 1, event_logger)
    testes_neonatais.set_resource_name('tec_enf_neonatal')

    # Aguarda o sinal a ser emitido pela mãe
    aguarda_alta = AguardaAltaBlock('Aguarda_Alta', model.env, event_logger)


    # Decide Aloj Conjunto ou Sozinha (baseado em filho.decide_ucp)  e  Tempo de Aloj (baseado em tipo_parto)
    decide_aloj = DecideBlock('Decide_Aloj', model.env, decision_type='condition', event_logger=event_logger)
    decide_aloj.add_route('Conjunto_Normal', next_block=None, condition= lambda e: (e.get_attribute('filho').get_attribute('decide_ucp') == False) and
                                                                                    e.get_attribute('tipo_parto') == 'normal')
    decide_aloj.add_route('Conjunto_Cesarea', next_block=None, condition= lambda e: (e.get_attribute('filho').get_attribute('decide_ucp') == False) and
                                                                                    e.get_attribute('tipo_parto') == 'cesarea')
    decide_aloj.add_route('Sozinha_Normal', next_block=None, condition= lambda e: (e.get_attribute('filho').get_attribute('decide_ucp') == True) and
                                                                                    e.get_attribute('tipo_parto') == 'normal')
    decide_aloj.add_route('Sozinha_Cesarea', next_block=None, condition= lambda e: (e.get_attribute('filho').get_attribute('decide_ucp') == True) and
                                                                                    e.get_attribute('tipo_parto') == 'cesarea')
    

    aloj_conjunto_normal = ProcessBlock('Aloj_Conjunto_Normal', model.env, lambda: distributions('alojamento_pos_parto_normal'), alojamento, 1, event_logger)
    aloj_conjunto_normal.set_resource_name('alojamento')
    aloj_conjunto_cesarea = ProcessBlock('Aloj_Conjunto_Cesarea', model.env, lambda: distributions('alojamento_pos_parto_cesarea'), alojamento, 1, event_logger)
    aloj_conjunto_cesarea.set_resource_name('alojamento')
    # Emite sinal para Alta Conjunta
    alta_conjunta = DisparaAltaBlock('Alta_Conjunta', model.env, event_logger)

    aloj_sozinha_normal = ProcessBlock('Aloj_Sozinha_Normal', model.env, lambda: distributions('alojamento_pos_parto_normal'), alojamento, 1, event_logger)
    aloj_sozinha_normal.set_resource_name('alojamento')
    aloj_sozinha_cesarea = ProcessBlock('Aloj_Sozinha_Cesarea', model.env, lambda: distributions('alojamento_pos_parto_cesarea'), alojamento, 1, event_logger)
    aloj_sozinha_cesarea.set_resource_name('alojamento')


    exam_obs = ProcessBlock(
        'Exames_e_Observacao', model.env,
        resource=None,  # apenas delay
        delay_time= lambda: distributions('exames_observacao'),
        event_logger=event_logger
    )


    saida = DisposeBlock("Saida", model.env, event_logger=event_logger)
    internacao = DisposeBlock('Internacao', model.env, event_logger=event_logger)


    # Adicionando os blocos ao modelo
    for block in [chegadas, recepcao, triagem, consulta, tratamento, procEsp, define_parto, exam_obs, internacao, saida,
                  inducao, inducao_funcionou, trabalho_parto, parto_normal, parto_cesarea, pos_parto, nascimento, aval_inicial,
                  precisa_ucp, ucp, ucp_funcionou, obito_rn, decide_aloj, aloj_sozinha_normal, aloj_sozinha_cesarea, testes_neonatais,
                  aloj_conjunto_normal, aloj_conjunto_cesarea, aguarda_alta, alta_conjunta]:
        model.add_block(block)

    # Conectando o fluxo -- GESTANTE
    chegadas.connect_to(recepcao)
    recepcao.connect_to(triagem)
    triagem.connect_to(consulta)
    consulta.connect_to(tratamento)

    tratamento.routes['Saida']["block"] = saida
    tratamento.routes['Proc_Esp']["block"] = procEsp
    tratamento.routes['Parto']["block"] = define_parto
    tratamento.routes['Internacao_ext']["block"] = internacao
    tratamento.routes['Exames_Observacao']["block"] = exam_obs

    procEsp.connect_to(saida)


    define_parto.routes['Trabalho_Parto']['block'] = trabalho_parto
    define_parto.routes['Cesarea_risco']['block'] = parto_cesarea
    define_parto.routes['Inducao']['block'] = inducao

    inducao.connect_to(inducao_funcionou)

    inducao_funcionou.routes['Sim']['block'] = trabalho_parto    # parto normal
    inducao_funcionou.routes['Nao']['block'] = parto_cesarea     # cesárea

    trabalho_parto.connect_to(parto_normal)

    parto_normal.connect_to(nascimento)
    parto_cesarea.connect_to(nascimento)

    # Conecte o nascimento
    nascimento.connect_to(pos_parto)      # Mãe -> pos_parto -> alojamento
    pos_parto.connect_to(decide_aloj)

    decide_aloj.routes['Conjunto_Normal']['block'] = aloj_conjunto_normal
    decide_aloj.routes['Conjunto_Cesarea']['block'] = aloj_conjunto_cesarea
    decide_aloj.routes['Sozinha_Normal']['block'] = aloj_sozinha_normal
    decide_aloj.routes['Sozinha_Cesarea']['block'] = aloj_sozinha_cesarea

    aloj_sozinha_normal.connect_to(saida)
    aloj_sozinha_cesarea.connect_to(saida)

    aloj_conjunto_normal.connect_to(alta_conjunta)
    aloj_conjunto_cesarea.connect_to(alta_conjunta)

    alta_conjunta.connect_to(saida)


    exam_obs.connect_to(consulta)

    # ---------------------------------------------------------------
    # CONECTANDO O FLUXO -- RN
    nascimento.connect_rn_to(aval_inicial)   # RN vai para avaliação inicial
    aval_inicial.connect_to(precisa_ucp)

    precisa_ucp.routes['Sim']['block'] = ucp
    precisa_ucp.routes['Nao']['block'] = testes_neonatais  # Aguarda a alta da mãe

    ucp.connect_to(ucp_funcionou)

    ucp_funcionou.routes['Sim']['block'] = saida   # Recebe alta (sozinho) após UCP
    ucp_funcionou.routes['Nao']['block'] = obito_rn

    testes_neonatais.connect_to(aguarda_alta)
    aguarda_alta.connect_to(saida)


    # ============================================================
    # Financial Attributes
    # ============================================================

    consulta.assign_attributes(cost= 595.90, revenue= 10.00)

    procEsp.assign_attributes(cost= 39.03, revenue= 109.29)  # cost= 1296.91/dia

    exam_obs.assign_attributes(cost= 129.57, revenue= 26.26)  # cost= 1036.55/dia

    parto_normal.modify_attributes(cost= lambda c: 4744.13)
    parto_normal.modify_attributes(revenue= lambda r: 443.40)

    parto_cesarea.modify_attributes(cost= lambda c: 6330.20)
    parto_cesarea.modify_attributes(revenue= lambda r: 890.94)

    ucp.assign_attributes(cost= 24683.50, revenue= 6136.67)  # cost= 3378.73/dia ; revenue= 840/dia

    aloj_conjunto_normal.assign_attributes(cost= 1905.70, revenue= 154.30)   # cost= 1905.70/dia
    aloj_sozinha_normal.assign_attributes(cost= 1905.70, revenue= 154.30)

    aloj_conjunto_cesarea.assign_attributes(cost= 3811.40, revenue= 308.60)  # cost= 1905.70/dia
    aloj_sozinha_cesarea.assign_attributes(cost= 3811.40, revenue= 308.60)



    return model


# ================================================================
# Funções de Pós-Processamento
# ================================================================
def analisar_fila_por_prioridade(model, atividade_alvo="Consulta"):
    dados = []
    for dispose_block in model.dispose_blocks:
        for entity in dispose_block.disposed_entities:
            if entity.get_attribute('disposal_time', 0) < model.warm_up_period:
                continue
            if not str(entity.id).startswith('Gestante'):
                continue
            
            prioridade = entity.get_attribute('priority', entity.priority)
            tempo_fila = entity.get_attribute(f"{atividade_alvo}_queue_time")
            
            if tempo_fila is not None:
                dados.append({
                    'ID': entity.id,
                    'Prioridade': prioridade,
                    'Tempo_Fila_Minutos': tempo_fila
                })
                
    if not dados:
        return pd.DataFrame()
        
    df = pd.DataFrame(dados)
    resumo = df.groupby('Prioridade').agg(
        Total_Pacientes=('ID', 'count'),
        Tempo_Medio_Fila=('Tempo_Fila_Minutos', 'mean'),
        Tempo_Maximo_Fila=('Tempo_Fila_Minutos', 'max')
    ).reset_index()
    
    resumo['Tempo_Medio_Fila'] = resumo['Tempo_Medio_Fila'].round(2)
    resumo['Tempo_Maximo_Fila'] = resumo['Tempo_Maximo_Fila'].round(2)
    return resumo


def analisar_filas_multiplas(model, atividades=["Recepcao", "Triagem", "Consulta", "ProcEspecial", "Inducao", "Parto_Normal", "Parto_Cesarea"]):
    """
    Extrai os tempos médios e máximos de fila para múltiplas atividades simultaneamente,
    agrupados pela classificação de risco (prioridade) da paciente.
    """
    dados = []
    
    # Percorre as entidades finalizadas
    for dispose_block in model.dispose_blocks:
        for entity in dispose_block.disposed_entities:
            
            # Ignora warm-up e recém-nascidos
            if entity.get_attribute('disposal_time', 0) < model.warm_up_period:
                continue
            if not str(entity.id).startswith('Gestante'):
                continue
            
            prioridade = entity.priority
            
            # Loop dinâmico pelas atividades solicitadas
            for atividade in atividades:
                tempo_fila = entity.get_attribute(f"{atividade}_queue_time")
                
                # Se a paciente passou por esse bloco e pegou fila (mesmo que 0 min)
                if tempo_fila is not None:
                    dados.append({
                        'Prioridade': prioridade,
                        'Atividade': atividade,
                        'Tempo_Fila': tempo_fila
                    })
                    
    if not dados:
        return pd.DataFrame()
        
    df = pd.DataFrame(dados)
    df.to_csv('arquivo.csv', index=False)
    
    # 3. Cria a Tabela Cruzada (Pivot) calculando Média e Máximo de uma só vez
    resumo = pd.pivot_table(
        df,
        values='Tempo_Fila',
        index='Prioridade',
        columns='Atividade',
        aggfunc=['count', 'mean', 'max'], # Calcula os dois cenários
        fill_value=0
    ).round(2)
    
    return resumo


# ================================================================
# Single Replication
# ================================================================
def main():

    event_logger = EventLogger()

    model = build_model(event_logger=event_logger, verbose=False)


    model.run_simulation(
        until=1440*30,         # *30*12
        warm_up_period=5000,  # 60 * 250
        seed=123
    )

    # =====================================================
    # Report results
    # =====================================================
    from desk.analytics.reporting import SimulationReporter
    reporter = SimulationReporter(model)
    reporter.print_results()
    # reporter._print_activity_metrics()
    # reporter._print_resource_metrics()
    # reporter._print_entity_counts()
    # reporter._print_block_statistics()

    # ---> INSERIR AQUI <---
    # print("\n" + "="*80)
    # print("ANÁLISE DE FILA POR PRIORIDADE (MANCHESTER) - CONSULTA")
    # print("="*80)
    # df_prioridades = analisar_fila_por_prioridade(model, atividade_alvo="Consulta")
    # print(df_prioridades.to_string(index=False))
    # print("="*80 + "\n")
    # ----------------------

    # ---> INSERIR AQUI <---
    print("\n" + "="*80)
    print("ANÁLISE DE FILAS (MÉDIA E MÁXIMO) POR PRIORIDADE DE RISCO")
    print("="*80)
    
    # Passamos os name_blocks
    setores_alvo = [ "Consulta", "Inducao", "Parto_Normal", "Parto_Cesarea"]
    
    df_filas = analisar_filas_multiplas(model, atividades=setores_alvo)
    print(df_filas)
    print("="*80 + "\n")

    '''
    # Trace de Entidades Específicas para avaliar Alta Conjunta
    print("\n" + "="*80)
    print("FILTER: Journey of Gestante_2")
    print("="*80)    
    model.trace_entity('Gestante_2')
    
    print("\n" + "="*80)
    print("FILTER: Journey of RN_Gestante_2")
    print("="*80)    
    model.trace_entity('RN_Gestante_2')
    '''

    # 4. Plotting
    print("\nPlotting resourse use over time...")
    plotter = SimulationPlotter(model)
    
    # Plot resource utilization over time
    plotter.plot_resource_use_over_time(show_warm_up=True, resource='med_obstetra', moving_average_window=50)
    # plotter.plot_resource_use_over_time(show_warm_up=True, resource='leito_inducao', moving_average_window=50)
    # plotter.plot_resource_use_over_time(show_warm_up=True, resource='enf_neonatal', moving_average_window=50)
    # plotter.plot_resource_use_over_time(show_warm_up=True, resource='alojamento', moving_average_window=50)
    # plotter.plot_resource_use_over_time(show_warm_up=True, resource='leito_ucp', moving_average_window=50)
    # plotter.plot_wip_over_time()
    # plotter.plot_system_time_distribution()

    # Plot activity metrics
    print("\nPlotting activity metrics...")
    reporter._print_activity_metrics()
    # plotter.plot_activity_metrics()

    # Plot resources utilization summary
    print("\nPlotting resourse summary...")
    # plotter.plot_resources_utilization()
    reporter._print_resource_metrics()
    reporter._print_entity_counts()
    reporter._print_block_statistics()

    # 5. Export event log
    # print("\nExporting event log...")
    # df = event_logger.export_to_csv("results/maternidade_event_log.csv")
    # print(f"\nFirst 10 events:")
    # print(df.head(10))

    # Financial analysis
    print("\nPlotting financial analysys...")
    financial_analyzer = FinancialAnalyzer(model)
    financial_analyzer.print_financial_summary()
    # financial_analyzer.plot_financial_breakdown()

    
    return model, event_logger


# ================================================================
# Full Simulation
# ================================================================
def simulation_wrapper(seed=None, until=None, warm_up_period=None):
    
    event_logger = EventLogger()

    config = SimulationConfig(
        duration=1440*30,
        warm_up_period= 5000,  # 15000
        seed=123,
        check_stability=True
    )

    model = build_model(config.duration, event_logger, verbose=False)

    model.run_simulation(
        validate_resources=False,
        until=until,
        seed=seed,
        warm_up_period=warm_up_period
    )

    return model


def run_replications():

    replication_framework = ReplicationFramework(
        simulation_function=simulation_wrapper,
        n_replications=24
    )

    replication_framework.run_replications(  # Ajustar until e warm_up_period
        base_seed=12345,
        until=1440*30,
        warm_up_period = 5000
    )

    # Access results
    df = replication_framework.get_results_dataframe()
    print(df.describe())


    # ---> INSERIR AQUI <---
    print("Gerando gráficos acadêmicos...")
    gerar_graficos_artigo(df)


    # import matplotlib.pyplot as plt

    # df[['system_time_avg', 'average_wip']].plot(kind='box')
    # plt.title('Distribuição das métricas por réplica')
    # plt.show()

    # df[['total_revenue', 'total_costs', 'net_profit']].plot(kind='bar')
    # plt.title('Resultados financeiros por réplica')
    # plt.show()


def gerar_graficos_artigo(df):
    """
    Gera gráficos estatísticos de alta qualidade para o artigo 
    com base no DataFrame de múltiplas replicações.
    """
    sns.set_theme(style="whitegrid") # Fundo branco, ideal para artigos
    
    # ==========================================
    # GRÁFICO 1: Tempos de Fila com IC 95%
    # ==========================================
    # Filtra as colunas que representam fila
    colunas_fila = [col for col in df.columns if col.endswith('_queue_time')]
    
    if colunas_fila:
        # Prepara os dados para o Seaborn (formato longo)
        df_fila = df.melt(value_vars=colunas_fila, var_name='Atividade', value_name='Tempo_Minutos')
        # Limpa os nomes para o gráfico ficar bonito
        df_fila['Atividade'] = df_fila['Atividade'].str.replace('_queue_time', '')
        
        plt.figure(figsize=(10, 6))
        # O barplot do seaborn já calcula o IC de 95% automaticamente (errorbar='ci')
        ax = sns.barplot(
            data=df_fila,
            x='Atividade',
            y='Tempo_Minutos',
            capsize=0.1,
            err_kws={'linewidth': 2},
            errorbar=('ci', 95),
            color='steelblue',
            edgecolor='black'
        )

        for p in ax.patches:
            height = p.get_height()
            ax.annotate(
                f'{height:.1f}',
                xy=(p.get_x() + p.get_width() / 2, height),
                xytext=(0, 5),
                textcoords='offset points',
                ha='center',
                va='bottom',
                fontsize=10
            )

        plt.title('Tempo Médio de Espera por Atividade (IC 95%)', fontsize=14, weight='bold')
        plt.ylabel('Tempo (minutos)', fontsize=12)
        plt.xlabel('Atividade', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        # plt.savefig('resultados_filas_ic95.png', dpi=300) # Salva em alta resolução
        plt.show()
        plt.close()

    # ==========================================
    # GRÁFICO 2: PAINEL FINANCEIRO DUPLO (Macro e Micro)
    # ==========================================
    # Cria uma figura com 1 linha e 2 colunas
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # --- FACETA (A): Balanço Macro ---
    colunas_macro = ['total_revenue', 'total_costs', 'net_profit']
    if all(col in df.columns for col in colunas_macro):
        df_macro = df.melt(value_vars=colunas_macro, var_name='Indicador', value_name='Valor (R$)')
        map_nomes = {'total_revenue': 'Receita Total', 'total_costs': 'Custo Total', 'net_profit': 'Resultado Líquido'}
        df_macro['Indicador'] = df_macro['Indicador'].map(map_nomes)
        
        sns.barplot(
            data=df_macro,
            x='Indicador',
            y='Valor (R$)',
            capsize=0.1,
            err_kws={'linewidth': 2},
            errorbar=('ci', 95),
            palette=['#2ecc71', '#e74c3c', '#34495e'],
            edgecolor='black',
            hue='Indicador',
            legend=False,
            ax=axes[0]) # Direciona para o eixo 0 (esquerda)
        
        axes[0].axhline(0, color='black', linewidth=1)
        axes[0].set_title('(A) Balanço Financeiro Global', fontsize=12, weight='bold')
        axes[0].set_ylabel('Montante Financeiro (R$)', fontsize=12)
        axes[0].set_xlabel('')
        
    # --- FACETA (B): Custos por Setor (Micro) ---
    colunas_custo_ativ = ['Consulta_total_cost', 'Exames_total_cost', 'Aloj_total_cost', 'ProcEspecial_total_cost', 'UCP_total_cost']
    colunas_presentes = [col for col in colunas_custo_ativ if col in df.columns]
    
    if colunas_presentes:
        df_ativ = df.melt(value_vars=colunas_presentes, var_name='Atividade', value_name='Custo (R$)')
        df_ativ['Atividade'] = df_ativ['Atividade'].str.replace('_total_cost', '')
        
        sns.barplot(
            data=df_ativ,
            x='Atividade',
            y='Custo (R$)',
            capsize=0.1,
            err_kws={'linewidth': 2},
            errorbar=('ci', 95),
            color='indianred',
            edgecolor='black',
            ax=axes[1]) # Direciona para o eixo 1 (direita)
        
        axes[1].set_title('(B) Decomposição de Custos por Setor', fontsize=12, weight='bold')
        axes[1].set_ylabel('Custo Total (R$)', fontsize=12)
        axes[1].set_xlabel('Setor / Atividade', fontsize=12)
        axes[1].tick_params(axis='x', rotation=45)

    # Título geral para a figura toda
    plt.suptitle('Análise Financeira do Cenário Atual - 30 Dias (IC 95%)', fontsize=16, weight='bold')
    
    # Ajusta os espaçamentos para nada ficar sobreposto
    plt.tight_layout()
    # plt.savefig('resultados_financeiros_painel_ic95.png', dpi=300)
    plt.show()
    plt.close()
        
    print("\nGráficos de Filas e Financeiros gerados com sucesso e salvos no formato PNG (dpi=300).")


# ================================================================
# Simulation Kit
#=================================================================

# Run a single replication
def run_single_replication():
    return main()

# Run a Full Simulation
def run_replications_cli():
    run_replications()

# Run the simulation with interface 
def run_visualization_cli(simulation_time=1440*30):
    return run_visualization(build_model, simulation_time=simulation_time)