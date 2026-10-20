# ADR063 — Faz62 yerel bounded replay ve özel hedefler

2026-10-15, DEC62-01; yalnız açık Faz62 kullanıcı talimatı.

Değişmez yerel snapshot'ı kontrollü bloklarla append simüle et. Processing clock
kaynak verisi, event watermark/late politikası explicit. Tam numeric checkpoint ve
parent ACK, iptalde durable chunk sınırına rollback, next cursor/strict event ID;
external broker exactly-once iddiası yok. Tek mevcut registry/ProjectStore/Provenance.
Scaler coordinate değişiminde SGD katsayılarını yeniden ifade et; delayed label'a
ait eski prediction scorelanır. Drift reset yalnız açık policy ile.

Özel hedefleri ayrı şemalarla ve explicit development role ile sınırla. Ordinal
numeric regression değildir. LabelPropagation eval feature katılımı transductive.
PU ve broker unavailable; özel hedef model persistence/new-data predict yok.

[Uygulama, kanıt ve resmî açıklar](../evidence/PHASE62.md). Önceki resmî kabul ve
2GiB GUI kapısı korunur. Faz63 bu kararın kapsamında değildir.
