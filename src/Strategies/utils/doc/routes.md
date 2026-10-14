# Routes et formats de réponse : guide pour écrire une stratégie

*Rédigé le 2026-10-13. Décrit le code tel qu'il est à cette date (sections 1 à 6) et les routes à créer (section 7).*
*Spécification des paquets utilitaires `state` et `calc` : [`docs/04-utils-strategie.md`](../../../../../docs/04-utils-strategie.md).*

---

## 1. Qui parle à qui

La stratégie ne fait **jamais** d'appel réseau elle-même. Elle retourne une ou plusieurs requêtes depuis `ProcessPrice`. `ConnStrat` les envoie au broker une par une et lui renvoie chaque réponse dans `ProcessResponse`.

```
TEST ──tick (TCP 8000)──▶ StratConn : ConnStrat.UpdatePrice
                                   └─▶ strategie.ProcessPrice(price, ts)  ─▶ requête, liste de requêtes ou None
                                   └─▶ pour chaque requête, dans l'ordre :
                                         GateComm ──HTTP POST 8080──▶ Sisimulation (broker)
                                         strategie.ProcessResponse(REQUEST.X, réponse_broker)
     ◀──{status, data:{actions:[{action, response}, ...]}}──
TEST ──même tick (TCP 443)──▶ Sisimulation : PRICE_UPDATE, ordres LIMIT, TP/SL, liquidation
```

Conséquences :

- **Plusieurs requêtes par tick, décidées d'avance.** La liste est fixée au retour de `ProcessPrice`. `ProcessResponse` voit chaque réponse avant l'envoi de la suivante, mais ne peut ni ajouter ni retirer de requête. Si une requête échoue, les suivantes partent quand même.
- **Toutes les requêtes d'un tick voient la même bougie** du broker : il ne reçoit le tick suivant qu'après la réponse de StratConn.
- **Le broker a un tick de retard sur la stratégie.** TEST envoie le tick N à StratConn, attend sa réponse, puis l'envoie au broker. Pendant `ProcessPrice(N)`, la bougie courante du broker est donc encore N−1 :
  - un ordre MARKET s'exécute au `close` du tick **N−1**, pas au `price` reçu par la stratégie ;
  - `GET_PRICE` renvoie le `close` de N−1 ;
  - au **premier tick**, le broker n'a reçu aucune bougie : toute requête tombe sur P7 (voir 6.3). Ne rien envoyer au premier tick.
- Les ordres LIMIT, TP, SL et liquidations du tick N sont traités **après** `ProcessPrice(N)`, quand le broker reçoit le tick N.

## 2. Contrat de la classe stratégie

Fichier dans `StratConn/src/Strategies/`, chargé par `strategie_path` dans `StratConn/src/main.py` (ex. `'Strategies.RouteTestStrat'`). La classe doit s'appeler `strategie`.

| Méthode | Obligatoire | Appelée par | Arguments | Retour |
|---|---|---|---|---|
| `ProcessPrice(price, ts)` | oui | `ConnStrat.UpdatePrice`, à chaque tick | `price` : `float` (`close` du tick) ; `ts` : `int`, epoch en **ms** | une requête, une **liste** de requêtes (envoyées dans l'ordre), ou `None` (= `STILL`) |
| `ProcessResponse(request, response)` | non | `ConnStrat.SendRequest`, juste après **chaque** appel broker | `request` : membre de `REQUEST` ; `response` : `dict` JSON du broker (section 4) | ignoré |
| `ProcessEvent(type, data)` | oui | `ConnStrat.SendEvent` (route `SEND_EVENT` de StratConn) | `type` : **chaîne** (`'POSITION_OPENED'`), pas l'enum ; `data` : `dict` | renvoyé tel quel à l'appelant HTTP |

Seul le `close` est transmis à la stratégie. `open`, `high`, `low` et `volume` ne lui parviennent pas.

### Requêtes que `ProcessPrice` peut retourner

`REQUEST` vient de `Core/request.py`. Tout est passé sous la clé `'params'`.

| `request` | `params` | Envoyé au broker |
|---|---|---|
| `REQUEST.STILL` | (aucun) | rien. Action TCP `{'action': 'still'}` ; `ProcessResponse` **n'est pas appelé** |
| `REQUEST.SUBMIT_ORDER` | un objet `Core.order.Order` | `SUBMIT_ORDER` avec `asdict(order)` |
| `REQUEST.CANCEL_ORDER` | `{'OrderId': int}` | `CANCEL_ORDER` |
| `REQUEST.CLOSE_POSITION` | `{'PositionId': int}` | `CLOSE_POSITION` |
| `REQUEST.GET_PRICE` | (aucun) | `GET_PRICE` |
| `REQUEST.GET_ORDERS`, `REQUEST.GET_POSITIONS` | `{'status': 'PENDING'}` optionnel | `GET_ORDERS` / `GET_POSITIONS` (**pas encore implémentées côté broker**, section 7) |
| `REQUEST.GET_WALLET` | (aucun) | `GET_WALLET` (**pas encore implémentée côté broker**) |

Une autre valeur produit l'action `{'action': 'unknown', 'request': ...}`, sans appel broker ni `ProcessResponse`, et passe le `status` de la réponse TCP à `FAILED`. Les autres requêtes de la liste sont tout de même envoyées.

Exemple : une requête seule.

```python
from Core.request import REQUEST
from Core.order import Order
from Core.tb_types import Asset, OrderStatus, OrderType, Side

def ProcessPrice(self, price, ts):
    order = Order(asset=Asset.BTC, asset_qty=0.01, base=Asset.USD, side=Side.LONG,
                  status=OrderStatus.REQUESTED, type=OrderType.MARKET,
                  leverage=1.0, tp_price=price * 1.03, sl_price=price * 0.98)
    return {'request': REQUEST.SUBMIT_ORDER, 'params': order}
```

Exemple : retourner la position dans le même tick (fermer le LONG, ouvrir un SHORT).

```python
def ProcessPrice(self, price, ts):
    short = Order(asset=Asset.BTC, asset_qty=0.01, base=Asset.USD, side=Side.SHORT,
                  status=OrderStatus.REQUESTED, type=OrderType.MARKET)
    return [{'request': REQUEST.CLOSE_POSITION, 'params': {'PositionId': self.long_id}},
            {'request': REQUEST.SUBMIT_ORDER, 'params': short}]
```

Si la fermeture échoue, le SHORT part quand même. Pour l'éviter, vérifier l'état avant de construire la liste (paquet `state`).

## 3. Format des objets sur le fil

- Les enums circulent par **nom** : `"LONG"`, `"MARKET"`, `"BTC"`, `"PENDING"`.
- Les prix sont des `float`. Les ids sont des `int` attribués par le broker, à partir de `0` pour les ordres et de `0` pour les positions, séparément.

### Order (réponse broker)

```json
{
  "id": 0, "asset": "BTC", "asset_qty": 0.01, "base": "USD",
  "side": "LONG", "status": "EXECUTED", "type": "MARKET",
  "leverage": 1.0, "level": 42000.0, "execution_price": 42000.0,
  "tp_price": 43260.0, "sl_price": 41160.0
}
```

| Champ | Envoyé par la stratégie | Rempli par le broker |
|---|---|---|
| `asset`, `base` | oui (`Asset`) | – |
| `asset_qty` | oui : taille **complète** de la position (le levier ne la multiplie pas) | – |
| `side` (`LONG`/`SHORT`), `type` (`MARKET`/`LIMIT`) | oui | – |
| `leverage` | optionnel, défaut `1.0` | – |
| `level` | **obligatoire en LIMIT** (prix d'exécution) ; ignoré en MARKET | MARKET : écrasé par le `close` courant du broker |
| `tp_price`, `sl_price` | optionnels (`null` = pas de TP/SL) | – |
| `status` | `REQUESTED` (ignoré) | `PENDING`, puis `EXECUTED` ou `CANCELLED` |
| `id` | ignoré | oui |
| `execution_price` | ne pas le remplir | à l'exécution |

### Position (réponse broker, événements)

```json
{
  "id": 0, "order_id": 0, "asset": "BTC", "asset_qty": 0.01, "base": "USD",
  "side": "LONG", "leverage": 1.0, "status": "CLOSED", "entry": 42000.0,
  "tp_price": 43260.0, "sl_price": 41160.0,
  "close_price": 42500.0, "close_justif": "TERM"
}
```

- `status` : `OPENED` ou `CLOSED`.
- `close_justif` : `TERM` (`CLOSE_POSITION`), `TP`, `SL` ou `LIQUIDATION`. `null` tant que la position est ouverte.
- `order_id` relie la position à l'ordre qui l'a ouverte. C'est le seul lien : la réponse à `SUBMIT_ORDER` ne contient **pas** l'id de la position.

## 4. Routes du broker (HTTP POST `127.0.0.1:8080/`)

Corps de toute requête : `{"request": NOM, "data": {...}}`. `GateComm` le construit pour vous.

### 4.1 `SUBMIT_ORDER`

- **Data :** l'`Order` (section 3). `status` et `id` sont ignorés.
- **Effet :** vérifie la marge (`disponible − prix × qty / leverage ≥ 0`), puis place l'ordre. Un MARKET est exécuté **dans la même requête** et ouvre une position.

| Cas | Réponse |
|---|---|
| Accepté, LIMIT | `{"status": "SUCCESS", "data": <Order PENDING>}` |
| Accepté, MARKET | `{"status": "SUCCESS", "data": <Order EXECUTED, execution_price rempli>}` |
| Marge insuffisante | `{"status": "FAILED", "data": {"reason": "Check margin not ok"}}` |

### 4.2 `CANCEL_ORDER`

- **Data :** `{"OrderId": int}`. Seul un ordre `PENDING` (un LIMIT pas encore touché) est annulable.

| Cas | Réponse |
|---|---|
| Annulé | `{"status": "SUCCESS", "data": <Order CANCELLED>}` |
| Id inconnu, ou ordre pas `PENDING` | `{"status": "FAILED", "data": {"reason": "Order <id> not found or not PENDING"}}` |

### 4.3 `CLOSE_POSITION`

- **Data :** `{"PositionId": int}`. Ferme au `close` courant du broker (N−1, voir section 1), `close_justif = TERM`.

| Cas | Réponse |
|---|---|
| Fermée | `{"status": "SUCCESS", "data": <Position CLOSED>}` |
| Id inconnu, ou position pas `OPENED` | `{"status": "FAILED", "data": {"reason": "Position <id> not found or not OPENED"}}` |

### 4.4 `GET_PRICE`

- **Data :** aucune.
- **Réponse :** `{"status": "success", "data": {"symbol": "BTCUSDT", "price": 42000.0}}`. `status` est en **minuscules** (héritage) et `symbol` est fixe.

### 4.5 `START_SIMULATION`

Envoyé par TEST, pas par une stratégie. Réponses : `{"status": "started", "message": ...}` ou `{"status": "already_running", "message": ...}`.

## 5. Routes de StratConn

| Canal | Requête | Réponse |
|---|---|---|
| HTTP POST `127.0.0.1:8081/` | `START_SIMULATION` | comme 4.5 ; ouvre le serveur TCP 8000 |
| HTTP POST `127.0.0.1:8081/` | `SEND_EVENT`, data `{"EventType": "POSITION_OPENED", "data": {...}}` | ce que retourne `strategie.ProcessEvent` |
| TCP `127.0.0.1:8000` (NDJSON) | un tick `{timestamp, timeframe, open, high, low, close, volume}` | `{"status": "success" \| "FAILED", "data": {"actions": [{"action": ..., "response": <réponse broker>}, ...]}}`. `action` vaut `still`, `submit_order`, `cancel_order`, `close_position`, `get_price`, `get_orders`, `get_positions`, `get_wallet` ou `unknown`. Sans requête : `[{"action": "still"}]`. `FAILED` si au moins une requête est inconnue |

**Aujourd'hui, personne n'appelle `SEND_EVENT`.** `ProcessEvent` n'est donc jamais appelé : la stratégie ne voit ni les TP/SL, ni les liquidations, ni l'exécution des LIMIT, ni l'id des positions ouvertes. La section 7 corrige ce manque.

## 6. Erreurs et réponses irrégulières

À tester dans `ProcessResponse` avant de lire `data` :

| # | Situation | Ce que reçoit la stratégie |
|---|---|---|
| 6.1 | Broker injoignable, erreur d'encodage | `{"status": "FAILED", "error": "<message>"}` (pas de `data`) — produit par `HTTPClient` |
| 6.2 | Nom de requête inconnu | `{"statut": "FAILED", "bc": "DUMB"}` (clé `statut`, héritage conservé) |
| 6.3 | Requête avant la première bougie du broker (**P7**) | `GET_PRICE` : `{"status": "failed", "data": {"info": "Not running"}}`. `SUBMIT_ORDER`, `CANCEL_ORDER`, `CLOSE_POSITION` : le broker plante sans répondre, donc 6.1 |
| 6.4 | JSON invalide | HTTP 400, donc 6.1 |
| 6.5 | Champ inconnu dans l'`Order`, ou LIMIT sans `level` | exception côté broker, pas de réponse, donc 6.1 |
| 6.6 | Nom d'enum invalide (`"long"`) | non converti, plante plus loin, donc 6.1 |

Test robuste du succès, valable pour toutes les routes :

```python
ok = str(response.get('status', '')).upper() == 'SUCCESS'
```

---

## 7. À créer

Décidé le 2026-10-13 : le broker **pousse** ses événements à StratConn, et trois routes de lecture permettent de se resynchroniser. Rien de cette section n'existe encore.

### 7.1 Format cible des réponses

Les nouvelles routes répondent toutes ainsi :

```json
{"status": "SUCCESS", "data": {...}}
{"status": "FAILED",  "data": {"reason": "<texte>"}}
```

`status` en majuscules, `data` toujours présent, enums par nom. Les routes existantes de la section 4 ne changent pas tant que leur normalisation n'est pas demandée (`GET_PRICE` en minuscules, `statut/DUMB`, P7).

Les routes de lecture fonctionnent **même avant la première bougie** : elles ne passent pas par le test `running` (pas de P7). Elles prennent `Simulation._lock`.

### 7.2 `GET_ORDERS` (broker)

- **Data :** `{"status": "PENDING"}` optionnel. Sans filtre, renvoie tous les ordres.
- **Réponse :** `{"status": "SUCCESS", "data": {"orders": [<Order>, ...]}}`, triés par `id`.
- **Erreur :** statut inconnu → `{"status": "FAILED", "data": {"reason": "Unknown status <x>"}}`.

### 7.3 `GET_POSITIONS` (broker)

- **Data :** `{"status": "OPENED"}` optionnel.
- **Réponse :** `{"status": "SUCCESS", "data": {"positions": [<Position>, ...]}}`, triées par `id`.

### 7.4 `GET_WALLET` (broker)

- **Data :** aucune.
- **Réponse :**

```json
{"status": "SUCCESS", "data": {
  "portfolio": {"USD": 10012.5},
  "locked":    {"USD": 420.0},
  "available": {"USD": 9592.5}
}}
```

`portfolio` est le solde, PnL réalisé compris. `locked` est la marge bloquée par les ordres `PENDING` et les positions `OPENED`. `available = portfolio − locked`. Les clés sont des noms d'`Asset` (le `Wallet` utilise des enums comme clés, à convertir).

### 7.5 Push des événements : broker → `SEND_EVENT` de StratConn

Un listener côté broker (`engine/`, sur le modèle de `TradeLogger`) envoie chaque événement sauf `PRICE_UPDATE` :

```json
POST 127.0.0.1:8081/
{"request": "SEND_EVENT", "data": {
  "EventType": "POSITION_OPENED",
  "data": {
    "timestamp": 1700000000000,
    "object": <Order ou Position>,
    "wallet": {"base": "USD", "portfolio": 10000.0, "locked": 420.0, "available": 9580.0}
  }
}}
```

| `EventType` | `object` | Quand |
|---|---|---|
| `ORDER_PLACED` | Order `PENDING` | `SUBMIT_ORDER` accepté |
| `ORDER_EXECUTED` | Order `EXECUTED` | MARKET immédiatement, LIMIT quand la bougie touche `level` |
| `ORDER_CANCELLED` | Order `CANCELLED` | `CANCEL_ORDER` accepté |
| `POSITION_OPENED` | Position `OPENED` | juste après `ORDER_EXECUTED` |
| `POSITION_CLOSED` | Position `CLOSED` (`close_justif` : `TERM`, `TP`, `SL`, `LIQUIDATION`) | `CLOSE_POSITION`, TP, SL ou liquidation |

Contraintes d'implémentation :

1. **Enregistrer le listener avant l'`Executor`** dans `Sisimulation/src/main.py`, comme `TradeLogger`. Sinon les événements arrivent en ordre inverse (`POSITION_OPENED` avant `ORDER_PLACED`) : voir `docs/trigger-events.md` §5.
2. **Envoi synchrone**, avec un timeout court. Avec un envoi synchrone, tous les événements du tick N arrivent avant `ProcessPrice(N+1)`, et ceux d'un MARKET arrivent **avant** la réponse à `SUBMIT_ORDER`.
3. Le wallet est copié au moment de l'événement (valeurs, pas de référence).
4. Un échec d'envoi est loggé (`[EVENT_PUSH]`) et n'interrompt pas le broker.

> **Piège : interblocage.** Le broker pousse l'événement en tenant `Simulation._lock`, et ses deux serveurs HTTP sont mono-thread. Si `ProcessEvent` appelait le broker (par exemple un `GET_WALLET`), cet appel attendrait le serveur HTTP du broker (occupé si l'événement vient d'une requête HTTP) ou `Simulation._lock` (tenu si l'événement vient d'un tick), alors que le broker attend lui-même la fin de `ProcessEvent` : blocage définitif. **`ProcessEvent` ne doit jamais appeler le broker.** Les resynchronisations passent par les requêtes retournées par `ProcessPrice`, quand le broker est libre.

### 7.6 Côté StratConn

| Fichier | Changement | État |
|---|---|---|
| `Core/request.py` | ajouter `GET_ORDERS`, `GET_POSITIONS`, `GET_WALLET` | fait (2026-10-13) |
| `GatewayCommand/StratCommand.py` | méthodes `get_orders(status=None)`, `get_positions(status=None)`, `get_wallet()` | fait (2026-10-13) |
| `TrackingEngine/ConnStrat.py` | router ces requêtes ; actions TCP `get_orders`, `get_positions`, `get_wallet` | fait (2026-10-13) |
| `Interfaces/WEB/HTTPClient.py` | ajouter un timeout à `urlopen` (aujourd'hui aucun : un broker bloqué fige StratConn) | à faire |

Tant que le broker n'a pas ces routes, il répond `{"statut": "FAILED", "bc": "DUMB"}` (section 6.2).

Les `params` côté stratégie : `{'status': 'PENDING'}` (optionnel) pour `GET_ORDERS` / `GET_POSITIONS`, rien pour `GET_WALLET`.
