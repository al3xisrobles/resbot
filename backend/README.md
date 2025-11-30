# Resy-Bot

Resy exposes a number of API endpoints for making reservations,
these can be investigated by taking a look at the `api.resy.com`
calls from the network tab. We can have some fun making automated
calls to those endpoints right when reservations become available

## Running

### Quick Setup

Run the setup script to create a virtual environment and install dependencies:

```bash
./setup.sh
```

Then activate the virtual environment:

```bash
source venv/bin/activate
```

### Manual Setup

If you prefer to set up manually:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Dependencies

Primary dependencies are pydantic, requests, rich, and questionary.
- `pydantic` is used for serializing/deserializing requests/responses from Resy
- `requests` handles HTTP calls to the Resy API
- `rich` provides beautiful console output
- `questionary` enables interactive prompts

### Local Configuration

The primary pieces of configuration for local execution are
defined in the `ResyConfig` and `TimedReservationRequest`
pydantic models in `resy_bot/models.py`.


#### ResyConfig

`ResyConfig` specifies credentials for personal Resy accounts.
Users should create a `credentials.json` file formatted as:
```json
{
  "api_key": "<api-key>",
  "token": "<api-token>",
  "payment_method_id": <payment-method>,
  "email": "<email>",
  "password": "<password>"
}
```

These values can be found in requests made in the Network tab.
- `api_key` can be found in the request headers under the
key `Authorization` in the format `ResyAPI api_key="<api-key>"`
- `token` can be found  in the request headers under the
key `X-Resy-Auth-Token`
- `payment_method_id` can be found in the request body to the endpoint
`/3/book`


#### TimedReservationRequest

In order to make a reservation right as it drops, a JSON
`TimedReservationRequest` must be created, see the following example
JSON:

```json
{
"reservation_request": {
  "party_size": 4,
  "venue_id": 12345,
  "window_hours": 1,
  "prefer_early": false,
  "ideal_date": "2023-03-30",
  "days_in_advance": 14,
  "ideal_hour": 19,
  "ideal_minute": 30,
  "preferred_type": "Dining Room"
},
  "expected_drop_hour": "10",
  "expected_drop_minute": "0"
}
```

These fields are mostly determined by the user:
- `party_size` is the number of members in the party
- `venue_id` is another field taken from communication in the
Network tab. This can be found as a URL param in requests to
the `/2/config` endpoint when navigating to the desired restaurant page
- `window_hours` is the number of hours before & after
the ideal hour/minute you are interested in
- `prefer_early` determines whether the earlier slot is selected when
2 time slots equidistant fom ideal hour/minute
- `ideal_date` is the date to search. This should not be provided if `days_in_advance` is used
- `days_in_advance` is the number of days from _now_ that the reservation becomes available. This should not be provided if `ideal_date` is used
- `ideal_hour` defines the hour field of the ideal timeslot
- `ideal_minute` defines the minute field of the ideal timeslot
- `preferred_type` is an optional field defining the type of seating
desired. If provided, Resy-Bot will _only_ search for that seating
type
- `expected_drop_hour` defines the hour field to of datetime
to start searching for slots
- `expected_drop_minute` defines the minute field to of datetime
to start searching for slots


### Running the Application

#### Interactive Mode (Recommended)

Run the interactive console UI (default):

```bash
python main.py
```

This provides a beautiful menu-driven interface to:
- 🔍 Search for restaurant info by venue ID
- 📅 Make reservations with guided prompts
- Easy navigation with arrow keys and Enter

#### File-Based Mode

Run with a reservation config file using the `-r` flag:

```bash
python main.py -r reservation.json
```

You can also specify a custom credentials file:

```bash
python main.py -c custom_credentials.json -r reservation.json
```

The application will wait until the time specified by
`expected_drop_hour` and `expected_drop_minute` to begin searching
for available timeslots and automatically book when found.

#### Help

View all options:

```bash
python main.py --help
```
