const gpmfExtract = require('gpmf-extract');
const goproTelemetry = require('gopro-telemetry');
const fs = require('fs');

const inputFile = process.argv[2];

fs.readFile(inputFile, (err, file) => {
    if (err) {
        console.error(err);
        process.exit(1);
    }

    gpmfExtract(file)
        .then(extracted => {
            goproTelemetry(extracted, {}, telemetry => {
                console.log(JSON.stringify(telemetry));
            });
        })
        .catch(error => {
            console.error(error);
            process.exit(1);
        });
});

