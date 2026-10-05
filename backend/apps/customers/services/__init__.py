"""Operações de escrita de clientes, um arquivo por agregado (docs/domain/customers.md).

Ordem de locks: cliente → segmento. A inativação de segmento trava só o segmento.
"""
