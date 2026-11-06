# Constituição do Projeto — Encurtador de URLs

Princípios que valem para todas as decisões deste projeto. Quando uma escolha
estiver em dúvida, ela deve ser resolvida a favor destes princípios.

## Propósito

Este é um projeto de **aprendizado**. Os objetivos são:

1. Aprender **Python** e o framework **Flask**.
2. Praticar **desenvolvimento guiado por specs**: constituição → spec → plano → tarefas.

O encurtador é o pretexto. Um produto pequeno e conhecido, para que a atenção
fique no processo e no aprendizado, não na complexidade do domínio.

## Princípios

### 1. Clareza antes de esperteza
O código deve ser fácil de ler por quem está aprendendo. Preferir soluções
diretas e explícitas a atalhos "mágicos". Se algo não é óbvio, um comentário
curto explica o porquê.

### 2. Uma regra, duas portas
As regras de negócio (validar, gerar código, salvar, contar cliques) ficam em
um único lugar, em Python puro, sem depender do Flask. A página web e a API são
apenas formas diferentes de chamar essas regras. Nenhuma regra é duplicada.

### 3. Todo requisito é verificável
Cada requisito da spec deve poder ser checado por um teste automatizado.
Os testes são escritos antes ou junto com o código (TDD), nunca "depois, se der tempo".

### 4. Escopo enxuto
Construir só o que a spec pede. Ideias novas vão para a lista de "versões
futuras" em vez de entrar no meio do trabalho.

### 5. Poucas dependências
Usar a biblioteca padrão do Python sempre que for razoável. Cada dependência
externa precisa de um motivo claro. Na v1: apenas Flask e pytest.

### 6. Portas abertas para o futuro
Não implementar o que não foi pedido, mas evitar decisões que fechem caminhos
já previstos. Em especial, o **login de usuários** (planejado para uma versão futura).

## Fora do propósito

- Rodar em produção, escala, alta disponibilidade.
- Proteção contra abuso (spam, links maliciosos, limite de requisições).
- Hospedagem e domínio próprio.
