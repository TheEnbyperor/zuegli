#ifndef SpecificConfigs_hpp
#define SpecificConfigs_hpp

#ifdef _MSC_VER
#ifdef DLL_EXPORTS
#define DLL_API __declspec(dllexport)
#else
#define DLL_API __declspec(dllimport)
#endif
#else
#define DLL_API __attribute__ ((visibility ("default")))
#endif

#include <string>
#include <stdexcept>

#define AZTEC_TYPENAME "Aztec";
#define AZTEC_COMPACT_TYPENAME "Aztec Compact";
#define QR_TYPENAME "QR";
#define QR_MICRO_TYPENAME "QR Micro";
#define CODE_128_TYPENAME "Code 128";
#define CODE_93_TYPENAME "Code 93";
#define CODE_39_TYPENAME "Code 39";
#define TELEPEN_TYPENAME "Telepen";
#define DOTCODE_TYPENAME "Dotcode";
#define CODE_32_TYPENAME "Code 32";
#define CODABAR_TYPENAME "Codabar";
#define CODE_11_TYPENAME "Code 11";
#define MSI_TYPENAME "MSI";
#define UPCA_TYPENAME "Upc-A";
#define UPCE_TYPENAME "Upc-E";
#define UPCE1_TYPENAME "Upc-E1";
#define EAN13_TYPENAME "Ean-13";
#define EAN8_TYPENAME "Ean-8";
#define PDF417_TYPENAME "PDF 417";
#define PDF417_MICRO_TYPENAME "PDF 417 Micro";
#define DATAMATRIX_TYPENAME "Data Matrix";
#define CODE_25_TYPENAME "Code 25";
#define INTERLEAVED_25_TYPENAME "Interleaved 2 of 5";
#define ITF_14_TYPENAME "ITF 14";
#define IATA_25_TYPENAME "IATA 25";
#define MATRIX_25_TYPENAME "Matrix 25";
#define DATALOGIC_25_TYPENAME "Datalogic 25";
#define COOP_25_TYPENAME "COOP 25";
#define DATABAR_14_TYPENAME "Databar 14";
#define DATABAR_LIMITED_TYPENAME "Databar Limited";
#define DATABAR_EXPANDED_TYPENAME "Databar Expanded";

#define ID_DOCUMENT_TYPENAME "ID Document";
#define ID_MRZ_TYPENAME "MRZ";
#define ID_PICTURE_TYPENAME "Picture";
#define ID_SIGNATURE_TYPENAME "Signature";


namespace NSBarkoder {
    class Config;

    class Rect {
    public:
        float left, top, width, height;

        Rect() {
            left = 0;
            top = 0;
            width = 100.0f;
            height = 100.0f;
        }

        Rect(float left, float top, float width, float height) {
            this->left = left;
            this->top = top;
            this->width = width;
            this->height = height;
        }
    };

    enum class DecodingSpeed {
        Fast = 0,
        Normal,
        Slow,
        Rigorous

    };

    enum class Formatting {
        Disabled = 0,
        Automatic,
        GS1,
        AAMVA,
    };

    enum class BarcodeType {
        Aztec,
        AztecCompact,
        QR,
        QRMicro,
        Code128,
        Code93,
        Code39,
        Codabar,
        Code11,
        Msi,
        UpcA,
        UpcE,
        UpcE1,
        Ean13,
        Ean8,
        PDF417,
        PDF417Micro,
        Datamatrix,
        Code25,
        Interleaved25,
        ITF14,
        IATA25,
        Matrix25,
        Datalogic25,
        COOP25,
        Code32,
        Telepen,
        Dotcode,
        IDDocument,
        IDMRZ,
        IDPicture,
        IDSignature,
        Databar14,
        DatabarLimited,
        DatabarExpanded
    };

    enum class DLL_API DecoderType {
        Aztec,
        AztecCompact,
        QR,
        QRMicro,
        Code128,
        Code93,
        Code39,
        Codabar,
        Code11,
        Msi,
        UpcA,
        UpcE,
        UpcE1,
        Ean13,
        Ean8,
        PDF417,
        PDF417Micro,
        Datamatrix,
        Code25,
        Interleaved25,
        ITF14,
        IATA25,
        Matrix25,
        Datalogic25,
        COOP25,
        Code32,
        Telepen,
        Dotcode,
        IDDocument,
        Databar14,
        DatabarLimited,
        DatabarExpanded
    };

enum class LengthType {
    Unlimited = 0

};

///////////////////////////////////////////////////////////////////////////////////////////////////
// Specific Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    // Base class for all specific configs
    class DLL_API SpecificConfig {

    public:

        enum class ChecksumType {
            Disabled,
            Enabled
        };

        bool enabled;
        int expectedCount = 0;
        int minimumLength;
        int maximumLength;
        int SetLengthRange(int minimumLength, int maximumLength) {

            if (minimumLength >= 0 && maximumLength >= 0){
                if (minimumLength > 0 && maximumLength > 0 && maximumLength < minimumLength){
                    throw std::invalid_argument( "Maximum length can't be smaller than minimum" );
                    return -1;
                } else {
                    this->minimumLength = minimumLength;
                    this->maximumLength = maximumLength;
                    return 0;
                }
            } else {
                throw std::invalid_argument( "Length must be positive number" );
                return -1;
            }
        }

        SpecificConfig(DecoderType decoderType);
        DecoderType Decoder();
        bool IsLicensed();
        const std::string& ConfigTypeName() const{
            return configTypeName;
        };
        virtual ~SpecificConfig() {}
        DecoderType decoderType;
    private:

    protected:
        std::string configTypeName;
    };


///////////////////////////////////////////////////////////////////////////////////////////////////
// Code 11 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API Code11Config : public SpecificConfig {
    public:
        enum class ChecksumType {
            Disabled,
            Single,
            Double
        };

        ChecksumType checksumType{ChecksumType::Disabled};

        Code11Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = CODE_11_TYPENAME;
        }
        virtual ~Code11Config() {};
    };


///////////////////////////////////////////////////////////////////////////////////////////////////
// Code 39 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API Code39Config : public SpecificConfig {
    public:
        enum class ChecksumType {
            Disabled,
            Enabled
        };

        ChecksumType checksumType{ChecksumType::Disabled};

        Code39Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = CODE_39_TYPENAME;
        }
        virtual ~Code39Config() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Telepen Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API TelepenConfig : public SpecificConfig {
    public:
        TelepenConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = TELEPEN_TYPENAME;
        }
        virtual ~TelepenConfig() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Dotcode Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API DotcodeConfig : public SpecificConfig {
    public:
        DotcodeConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = DOTCODE_TYPENAME;
        }
        virtual ~DotcodeConfig() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Code 32 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API Code32Config : public SpecificConfig {
    public:

        Code32Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = CODE_32_TYPENAME;
        }
        virtual ~Code32Config() {};
    };



///////////////////////////////////////////////////////////////////////////////////////////////////
// Msi Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API MsiConfig : public SpecificConfig {
    public:
        enum class ChecksumType {
            Disabled,
            Mod10,
            Mod11,
            Mod1010,
            Mod1110,
            Mod11IBM,
            Mod1110IBM
        };

        ChecksumType checksumType{ChecksumType::Mod10};

        MsiConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = MSI_TYPENAME;
            minimumLength = 5;
        }
        virtual ~MsiConfig() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Code 25 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API Code25Config : public SpecificConfig {
    public:


        ChecksumType checksumType{ChecksumType::Disabled};

        Code25Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = CODE_25_TYPENAME;
        }
        virtual ~Code25Config() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// IATA 25 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API IATA25Config : public SpecificConfig {
    public:


        Code25Config::ChecksumType checksumType{Code25Config::ChecksumType::Disabled};
        IATA25Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = IATA_25_TYPENAME;
        }
        virtual ~IATA25Config() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Matrix 25 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API Matrix25Config : public SpecificConfig {
    public:


        Code25Config::ChecksumType checksumType{Code25Config::ChecksumType::Disabled};
        Matrix25Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = MATRIX_25_TYPENAME;
        }
        virtual ~Matrix25Config() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Datalogic 25 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API Datalogic25Config : public SpecificConfig {
    public:


        Code25Config::ChecksumType checksumType{Code25Config::ChecksumType::Disabled};
        Datalogic25Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = DATALOGIC_25_TYPENAME;
        }
        virtual ~Datalogic25Config() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// COOP 25 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API COOP25Config : public SpecificConfig {
    public:


        Code25Config::ChecksumType checksumType{Code25Config::ChecksumType::Disabled};
        COOP25Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = COOP_25_TYPENAME;
        }
        virtual ~COOP25Config() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Interleaved 25 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API Interleaved25Config : public SpecificConfig {
    public:


        Code25Config::ChecksumType checksumType{Code25Config::ChecksumType::Disabled};

        Interleaved25Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = INTERLEAVED_25_TYPENAME;
        }
        virtual ~Interleaved25Config() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// ITF 14 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API ITF14Config : public SpecificConfig {
    public:

        ITF14Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = ITF_14_TYPENAME;
        }
        virtual ~ITF14Config() {};
    };


///////////////////////////////////////////////////////////////////////////////////////////////////
// Aztec Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API AztecConfig : public SpecificConfig {
    public:
        AztecConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = AZTEC_TYPENAME;
        }
        virtual ~AztecConfig() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// AztecCompact Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API AztecCompactConfig : public SpecificConfig {
    public:
        AztecCompactConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = AZTEC_COMPACT_TYPENAME;
        }
        virtual ~AztecCompactConfig() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Datamatrix Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API DatamatrixConfig : public SpecificConfig {
    public:
        int dpmMode = 0;
        DatamatrixConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = DATAMATRIX_TYPENAME;
        }
        virtual ~DatamatrixConfig() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// QR Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API QRConfig : public SpecificConfig {

    public:
        int dpmMode = 0;
        bool multiPartMerge = 0;
        QRConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = QR_TYPENAME;
        }
        virtual ~QRConfig() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// QRMicro Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API QRMicroConfig : public SpecificConfig {
    public:
        int dpmMode = 0;
        QRMicroConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = QR_MICRO_TYPENAME;
        }
        virtual ~QRMicroConfig() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Code128 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API Code128Config : public SpecificConfig {
    public:
        Code128Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = CODE_128_TYPENAME;
        }
        virtual ~Code128Config() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Code93 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API Code93Config : public SpecificConfig {
    public:
        Code93Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = CODE_93_TYPENAME;
        }
        virtual ~Code93Config() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Codabar Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API CodabarConfig : public SpecificConfig {
    public:
        CodabarConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = CODABAR_TYPENAME;
            minimumLength = 4;
        }
        virtual ~CodabarConfig() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// UpcA Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API UpcAConfig : public SpecificConfig {
    public:
        UpcAConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = UPCA_TYPENAME;
        }
        virtual ~UpcAConfig() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// UpcE Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API UpcEConfig : public SpecificConfig {
    public:
        bool expandToUPCA = false;
        UpcEConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = UPCE_TYPENAME;
        }
        virtual ~UpcEConfig() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// UpcE1 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API UpcE1Config : public SpecificConfig {
    public:
        bool expandToUPCA = false;
        UpcE1Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = UPCE1_TYPENAME;
        }
        virtual ~UpcE1Config() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Ean13 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API Ean13Config : public SpecificConfig {
    public:
        Ean13Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = EAN13_TYPENAME;
        }
        virtual ~Ean13Config() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Ean8 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API Ean8Config : public SpecificConfig {
    public:
        Ean8Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = EAN8_TYPENAME;
        }
        virtual ~Ean8Config() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// PDF417 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API PDF417Config : public SpecificConfig {
    public:
        PDF417Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = PDF417_TYPENAME;
        }
        virtual ~PDF417Config() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// PDF417Micro Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API PDF417MicroConfig : public SpecificConfig {
    public:
        PDF417MicroConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = PDF417_MICRO_TYPENAME;
        }
        virtual ~PDF417MicroConfig() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Databar 14 Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API Databar14Config : public SpecificConfig {
    public:
        Databar14Config(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = DATABAR_14_TYPENAME;
        }
        virtual ~Databar14Config() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// DatabarLimited Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API DatabarLimitedConfig : public SpecificConfig {
    public:
        DatabarLimitedConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = DATABAR_LIMITED_TYPENAME;
        }
        virtual ~DatabarLimitedConfig() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// Databar Expanded Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API DatabarExpandedConfig : public SpecificConfig {
    public:
        DatabarExpandedConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = DATABAR_EXPANDED_TYPENAME;
        }
        virtual ~DatabarExpandedConfig() {};
    };

///////////////////////////////////////////////////////////////////////////////////////////////////
// ID Document Config
///////////////////////////////////////////////////////////////////////////////////////////////////
    class DLL_API IDDocumentConfig : public SpecificConfig {
    public:
        ChecksumType masterChecksumType{ChecksumType::Disabled};
        IDDocumentConfig(DecoderType decoderType) : SpecificConfig (decoderType) {
            configTypeName = ID_DOCUMENT_TYPENAME;
        }
        virtual ~IDDocumentConfig() {};
    };
}



#endif // SpecificConfigs_hpp
