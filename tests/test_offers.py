from unittest.mock import MagicMock

import pytest

from safeway_coupons.client import SafewayClient
from safeway_coupons.models import OfferStatus

from .utils import create_offer


def client_for(payload):
    client = SafewayClient.__new__(SafewayClient)
    client.session = MagicMock(store_id="123")
    client._requests = MagicMock()
    response = client._requests.get.return_value
    response.status_code = 200
    response.json.return_value = payload
    return client


@pytest.mark.parametrize("key", ["companionGalleryOfferList", "companionGalleryOffer"])
def test_offer_formats(key):
    offer = create_offer("123")
    offer.status = OfferStatus.Clipped
    data = offer.to_dict(encode_json=True)
    collection = [data] if key.endswith("List") else {"123": data}
    offers = client_for({key: collection}).get_offers()
    assert len(offers) == 1
    assert offers[0].offer_id == "123"
    assert offers[0].status == OfferStatus.Clipped


@pytest.mark.parametrize("payload", [
    {"companionGalleryOfferList": []}, {"companionGalleryOffer": {}}
])
def test_empty_offers(payload):
    assert client_for(payload).get_offers() == []


@pytest.mark.parametrize("payload", [
    {}, {"error": "unauthorized"}, [],
    {"companionGalleryOffer": None},
    {"companionGalleryOffer": {"123": None}},
    {"companionGalleryOfferList": None},
])
def test_invalid_offers(payload):
    with pytest.raises(ValueError, match="Unexpected offers response"):
        client_for(payload).get_offers()
