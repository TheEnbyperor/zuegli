import ber_tlv.tlv
from django import template
import cryptography.x509
import cryptography.x509.oid
from ..vdv import util

register = template.Library()

@register.filter(name="oid")
def oid(value):
    if value == "1.2.840.10045.4.3.2":
        return "ECDSA with SHA256"
    elif value == "2.16.840.1.101.3.4.3.1":
        return "DSA with SHA224"
    elif value == "2.16.840.1.101.3.4.3.2":
        return "DSA with SHA256"
    elif value == "1.2.840.10040.4.1":
        return "DSA"
    elif value == "1.2.840.10045.2.1":
        return "Elliptic Curve"
    elif value == "1.2.840.10045.3.1.7":
        return "EC secp256r1"
    elif value == "1.2.840.10040.4.3":
        return "DSA with SHA1"
    elif value == "2.5.29.19":
        return "Basic constraints"
    elif value == "2.5.29.15":
        return "Key usage"
    elif value == "2.5.29.37":
        return "Extended key usage"
    elif value == "2.5.29.14":
        return "Subject key identifier"
    elif value == "2.5.29.35":
        return "Authority key identifier"
    elif value == "2.5.29.1":
        return "Authority key identifier (old)"
    elif value == "1.3.101.112":
        return "Ed25519"
    elif value == "1.2.840.113549.1.1.11":
        return "RSA with SHA256"
    elif value == "1.2.840.113549.1.1.12":
        return "RSA with SHA384"
    elif value == "1.2.840.113549.1.1.13":
        return "RSA with SHA512"
    elif value == "1.2.840.113549.1.1.14":
        return "RSA with SHA224"
    elif value == "1.2.804.2.1.1.1.1.3.6.1.1":
        return "DSTU 4145 with DSTU 7564-256 polynomial basis Little-Endian"
    elif value == "1.3.6.1.5.5.7.48.1":
        return "OCSP"
    elif value == "0.4.0.194121.1.1":
        return "ETSI Natural Person Semantics"
    else:
        return str(value)

@register.filter(name="is_rfc822_name")
def is_rfc822_name(value) -> bool:
    return isinstance(value, cryptography.x509.RFC822Name)

@register.filter(name="is_dns_name")
def is_dns_name(value) -> bool:
    return isinstance(value, cryptography.x509.DNSName)

@register.filter(name="is_directory_name")
def is_directory_name(value) -> bool:
    return isinstance(value, cryptography.x509.DirectoryName)

@register.filter(name="is_uri_name")
def is_uri_name(value) -> bool:
    return isinstance(value, cryptography.x509.UniformResourceIdentifier)

@register.filter(name="is_ip_name")
def is_ip_name(value) -> bool:
    return isinstance(value, cryptography.x509.IPAddress)

@register.filter(name="is_rid_name")
def is_rid_name(value) -> bool:
    return isinstance(value, cryptography.x509.RegisteredID)

UA_TAXPAYER_ID = [1, 2, 804, 2, 1, 1, 1, 11, 1, 4, 1, 1]
UA_LEGAL_ENTITY_ID = [1, 2, 804, 2, 1, 1, 1, 11, 1, 4, 2, 1]
UA_RESIDENT_ID = [1, 2, 804, 2, 1, 1, 1, 11, 1, 4, 3, 1]

@register.filter(name="decode_subject_directory_attributes")
def decode_subject_directory_attributes(value):
    d = ber_tlv.tlv.Tlv.parse(value)
    if len(d) != 1:
        return None
    if d[0][0] != 0x30:
        return None
    d = d[0][1]

    out = []
    for attr in d:
        if attr[0] != 0x30:
            return None
        attr = attr[1]
        if len(attr) not in (2, 3):
            return None
        aoid = attr[0]
        if aoid[0] != 0x06:
            return None
        aoid = util.decode_oid(aoid[1])

        value = attr[1]
        if value[0] != 0x31:
            return None
        value = value[1]

        if aoid == UA_TAXPAYER_ID:
            if len(attr) != 2:
                return None
            if len(value) != 1:
                return None
            value = value[0]
            if value[0] != 0x13:
                return None
            value = value[1].decode("ascii")
            out.append(("ua_taxpayer_id", value))
        elif aoid == UA_LEGAL_ENTITY_ID:
            if len(attr) != 2:
                return None
            if len(value) != 1:
                return None
            value = value[0]
            if value[0] != 0x13:
                return None
            value = value[1].decode("ascii")
            out.append(("ua_legal_entity_id", value))
        elif aoid == UA_RESIDENT_ID:
            if len(attr) != 2:
                return None
            if len(value) != 1:
                return None
            value = value[0]
            if value[0] != 0x13:
                return None
            value = value[1].decode("ascii")
            out.append(("ua_resident_id", value))
        else:
            out.append(("unknown", ".".join([str(k) for k in aoid])))

    return out

QC_COMPLIANCE = [0, 4, 0, 1862, 1, 1]
QC_MONETARY_VALUE = [0, 4, 0, 1862, 1, 2]
QC_PKI_DISCLOSURE_STATEMENTS = [0, 4, 0, 1862, 1, 5]
QC_LEGISLATION = [0, 4, 0, 1862, 1, 7]
RFC3739_SEMANTICS = [1, 3, 6, 1, 5, 5, 7, 11, 2]
UA_DIGITAL_SIG_LAW = [1, 2, 804, 2, 1, 1, 1, 2, 1]

@register.filter(name="decode_qualified_certificate_statements")
def decode_qualified_certificate_statements(value):
    d = ber_tlv.tlv.Tlv.parse(value)
    if len(d) != 1:
        return None
    if d[0][0] != 0x30:
        return None
    d = d[0][1]

    out = []
    for stmt in d:
        if stmt[0] != 0x30:
            return None
        stmt = stmt[1]
        if len(stmt) not in (1, 2):
            return None
        soid = stmt[0]
        if soid[0] != 0x06:
            return None
        soid = util.decode_oid(soid[1])

        if soid == QC_COMPLIANCE:
            if len(stmt) != 1:
                return None
            out.append(("qc_compliance", None))
        elif soid == QC_MONETARY_VALUE:
            if len(stmt) != 2:
                return None
            d = stmt[1]
            if d[0] != 0x30:
                return None
            d = d[1]
            if len(d) != 3:
                return None
            currency_code = d[0]
            if currency_code[0] == 0x13:
                currency_code = currency_code[1].decode("ascii")
            elif currency_code[0] == 0x02:
                currency_code = currency_code[1]
            else:
                return None
            amount = d[1]
            if amount[0] != 0x02:
                return None
            amount = int.from_bytes(amount[1], "big", signed=True)
            exponent = d[2]
            if exponent[0] != 0x02:
                return None
            exponent = int.from_bytes(exponent[1], "big", signed=True)
            out.append(("qc_monetary_value", {
                "currency_code": currency_code,
                "value": amount * (10 ** exponent),
            }))
        elif soid == QC_PKI_DISCLOSURE_STATEMENTS:
            if len(stmt) != 2:
                return None
            d = stmt[1]
            if d[0] != 0x30:
                return None
            pds_locs = []
            for loc in d[1]:
                if loc[0] != 0x30:
                    return None
                loc = loc[1]
                if len(loc) != 2:
                    return None
                url = loc[0]
                if url[0] != 0x16:
                    return None
                url = url[1].decode("ascii")
                lang = loc[1]
                if lang[0] != 0x13:
                    return None
                lang = lang[1].decode("ascii")
                pds_locs.append({
                    "url": url,
                    "language": lang,
                })
            out.append(("qc_pds_loc", pds_locs))
        elif soid == QC_LEGISLATION:
            if len(stmt) != 2:
                return None
            d = stmt[1]
            if d[0] != 0x30:
                return None
            cc = []
            for l in d[1]:
                if l[0] != 0x13:
                    return None
                cc.append(l[1].decode("ascii"))
            out.append(("qc_legislation", cc))
        elif soid == RFC3739_SEMANTICS:
            if len(stmt) != 2:
                return None
            d = stmt[1]
            if d[0] != 0x30:
                return None
            d = d[1]
            semantics = {}
            if len(d) not in (1, 2):
                return None
            if d[0][0] == 0x06:
                semantics["id"] = ".".join([str(k) for k in util.decode_oid(d[0][1])])
                if len(d) == 2:
                    if d[1][0] != 0x30:
                        return None
                    semantics["name_registration_authorities"] = d[1][1]
            elif d[0][0] == 0x30:
                semantics["name_registration_authorities"] = d[0][1]
            out.append(("rfc3739_semantics", semantics))
        elif soid == UA_DIGITAL_SIG_LAW:
            if len(stmt) != 1:
                return None
            out.append(("ua_digital_sig_law", None))
        else:
            out.append(("unknown", ".".join([str(k) for k in soid])))

    return out
