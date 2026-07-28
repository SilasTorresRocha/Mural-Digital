from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.banco_dados import Base

# Tabela associativa Muitos-para-Muitos entre Conteudo e Zona
conteudo_zona = Table(
    'conteudo_zona',
    Base.metadata,
    Column('conteudo_id', Integer, ForeignKey('conteudos.id'), primary_key=True),
    Column('zona_id', Integer, ForeignKey('zonas.id'), primary_key=True)
)

# Tabela associativa Muitos-para-Muitos entre Aviso e Zona
aviso_zona = Table(
    'aviso_zona',
    Base.metadata,
    Column('aviso_id', Integer, ForeignKey('avisos.id'), primary_key=True),
    Column('zona_id', Integer, ForeignKey('zonas.id'), primary_key=True)
)

class Zona(Base):
    __tablename__ = "zonas"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True) # Ex: "RU", "Setor N"
    modelo_tv = Column(String, default="2") #Eu gosto do modelo 2 kkkk
    
class Conteudo(Base):
    __tablename__ = "conteudos"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True)
    tipo_midia = Column(String) #  imagem ou video
    caminho_arquivo = Column(String)
    tempo_exibicao = Column(Integer, default=10) # Tempo em segundos (usado para imagens)
    ativo = Column(Boolean, default=True)
    
    # Relação com as zonas onde este vídeo/imagem deve tocar
    zonas = relationship("Zona", secondary=conteudo_zona, backref="conteudos")
    
class Aviso(Base):
    __tablename__ = "avisos"

    id = Column(Integer, primary_key=True, index=True)
    texto = Column(String(150), index=True) # Limite rígido no banco de 150 caracteres
    ativo = Column(Boolean, default=True)
    
    # Relação com as zonas onde este aviso/letreiro deve passar
    zonas = relationship("Zona", secondary=aviso_zona, backref="avisos")

class Configuracao(Base):
    __tablename__ = "configuracoes"

    id = Column(Integer, primary_key=True, index=True)
    chave = Column(String, unique=True, index=True)
    valor = Column(String) # Pode ser '0', '1' ou '2' para representar os Modelos

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True) # Nome de usuário
    senha_hash = Column(String) # Senha criptografada (bcrypt)


