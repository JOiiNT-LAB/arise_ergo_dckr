#!/bin/sh

echo "
========================================================

Starting inject.sh

========================================================
"

echo "
========================================================

Checking if automatic subscription is enabled..

========================================================
"

 if [ "$AUTOMATIC_SUBSCRIPTION" != "true" ] ; then
    echo 'Automatic subscription is disabled'
    exit 0
fi

# With network_mode: host (see docker-compose.yml) the service names do not resolve:
# CRATE_HOST and ORION_HOST are set to 127.0.0.1 there. The defaults match a
# compose network where the services are reachable by container name.
CRATE_HOST="${CRATE_HOST:-crate-db}"
ORION_HOST="${ORION_HOST:-orion}"

echo "
========================================================

Waiting for CrateDB to start..

========================================================
"

crate_response=$(curl -s "$CRATE_HOST:4200")
crate_status=$(echo "$crate_response" | jq '.status')

LOOPS=15
while [ "$crate_status" -ne 200 ]; do

    echo "
========================================================

Waiting for CrateDB to start..

========================================================
"

    sleep 15
    let LOOPS--
    if [ $LOOPS -eq 0 ] ; then
        echo 'CrateDB has not started :( :('
        exit 1
    fi

    crate_response=$(curl -s "$CRATE_HOST:4200")
    crate_status=$(echo "$crate_response" | jq '.status')

done

echo "
========================================================

CrateDB Started!

========================================================
"

echo "
========================================================

Waiting for Orion-LD to start..

========================================================
"

orion_status=$(curl -s -o /dev/null -w "%{http_code}" "$ORION_HOST:1026/version")

LOOPS=15
while [ "$orion_status" -ne 200 ]; do

    echo "
========================================================

Waiting for Orion-LD to start..

========================================================
    "

    sleep 15
    let LOOPS--
    if [ $LOOPS -eq 0 ] ; then
        echo 'Orion-LD has not started :( :('
        exit 1
    fi

        orion_status=$(curl -s -o /dev/null -w "%{http_code}" "$ORION_HOST:1026/version")

done

echo "
========================================================

Orion-LD Started!

========================================================
"

echo "
========================================================

Sending the subscription request..

========================================================
"
# Non-recursive: drop .json subscription files directly here, not in subfolders.
subscription_dir="/src/ngsi-timeseries-api/src/subscriptions"

if ! ls "$subscription_dir"/*.json >/dev/null 2>&1; then
    echo 'No subscription files found in '"$subscription_dir"' — skipping automatic subscription.'
    exit 0
fi

for subscription_file in "$subscription_dir"/*.json; do
    if [ -e "$subscription_file" ]; then
        # Optional multi-tenancy: the header is sent only when the file defines a tenant.
        tenant=$(jq -r '(.notification.endpoint.receiverInfo // [])[] | select(.key == "fiware-service") | .value' "$subscription_file")

        if [ -n "$tenant" ]; then
            subscription_status=$(curl -s -L -o /dev/null -w "%{http_code}" -X POST "http://$ORION_HOST:1026/ngsi-ld/v1/subscriptions/" \
            -H 'Content-Type: application/ld+json' \
            -H "NGSILD-Tenant: $tenant" \
            -d @"$subscription_file")
        else
            subscription_status=$(curl -s -L -o /dev/null -w "%{http_code}" -X POST "http://$ORION_HOST:1026/ngsi-ld/v1/subscriptions/" \
            -H 'Content-Type: application/ld+json' \
            -d @"$subscription_file")
        fi

        # The subscription is stored in MongoDB, so on every restart after the first
        # Orion answers 409 Conflict: that means it is already in place.
        if [ "$subscription_status" -eq 201 ] ; then
            echo "
========================================================

Subscription sent successfully!

========================================================
            "
        elif [ "$subscription_status" -eq 409 ] ; then
            echo "
========================================================

Subscription already exists, nothing to do.

========================================================
            "
        else
            echo "Subscription could not be sent (HTTP $subscription_status) :( :("
            exit 1
        fi
    else
        echo 'The subscription file could not be find :( :('
        exit 1
    fi
done
